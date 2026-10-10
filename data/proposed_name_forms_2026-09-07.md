# Ierosinātās `name_forms` 30 tukšajām rindām — operatora apstiprinājumam

Verdikts 34 (`docs/verdikti-2026-09-06.md`, D grupa). Sagatavots 2026-09-07.
**Nekas nav izpildīts.** Izpildāmais SQL: `data/fix_grupaD_name_forms_2026-09-07.sql`,
atcelšana: `data/rollback_grupaD_name_forms_2026-09-07.sql`.
`name_forms` nekad netiek pievienotas automātiski — tā ir operatora robeža.

---

## Divi mērījumi, kas maina verdikta pamatojumu

**1. Locījumi NEtrūkst.** Verdikta teikums «locījumu trūkums nozīmē, ka ģenitīvi un
datīvi šos cilvēkus nepiesaista vispār» nesakrīt ar kodu. `src/matcher.py::_load_politician_forms`
tukšām `name_forms` uzliek `[pilnais vārds, kailais uzvārds]` un tad
`_latvian_surname_inflections` pievieno locījumus. Pārbaudīts dzīvi (18 rindas):

| pārbaude | rezultāts |
|---|---|
| `pid=66` faktiskās formas | `['Anda Čakša', 'Čakša', 'Čakšas', 'Čakšai', 'Čakšu']` |
| `match_politicians("Andas Čakšas iniciatīva")` | `[(66, 'subject')]` — ģenitīvs strādā |
| `match_politicians("Briškenam jautāja")` | `[(67, 'subject')]` — datīvs strādā |
| `match_politicians("Cakša paziņoja")` | `[]` — **ASCII neatpazīst** |

Robs ir tikai ASCII variantos, un tikai tajos.

**2. ASCII robs korpusā ir gandrīz tukšs.** Skenēti **visi 89 649 dokumenti**
(virsraksts + saturs) ar 66 ierosinātajām ASCII formām, vārda robežas pārbaude tāda
pati kā `_occurrences` (blakus rakstzīme nedrīkst būt burts), papildus izslēdzot
`@handle` kontekstu. Rezultāts:

| forma | dokumenti | piemērs |
|---|---|---|
| `Briskens` | 1 | doc 46386 |
| `Briskena` | 1 | doc 87782 |
| `Briskenu` | 1 | doc 101920 |
| `Zuravleva` | 1 | doc 37508 |
| `Olegs Burovs` | 1 | doc 91177 |
| pārējās 61 forma | **0** | — |

Bez `@handle` izslēgšanas skaitļi izskatās lieli (`Briskens` 180, `Zalans` 65,
`Krustpunkta` 190), bet visi tie ir X handli — `@Briskens`, `@Janis_Zalans`,
`@Krustpunkta`. Tos matcher jau ķer pa H ceļu (reģistrētie handli no
`social_accounts` ∪ `x_handle` ir pilntiesīgas match formas kopš 2026-07-27), un
visām 26 personu/organizāciju rindām handle JAU ir reģistrēts. **Handle pārklājums
nav robs.**

**Ieteikums:** apstiprināt A grupu (3 rindas ar izmērītu ražu). B grupa ir
konvencijas pilnība ar izmērītu ražu 0 — apstiprināt vai atlikt pēc izvēles; katra
jauna ASCII kailā forma ir jauna substring virsma bez pierādīta ieguvuma.

---

## A grupa — izmērīta raža ≥1 dokuments (ieteikts apstiprināt)

| pid | vārds | ierosinātās `name_forms` |
|---|---|---|
| 67 | Kaspars Briškens | `["Kaspars Briškens", "Kaspars Briskens", "Briškens", "Briskens", "Briskena", "Briskenam", "Briskenu"]` |
| 74 | Oļegs Burovs | `["Oļegs Burovs", "Olegs Burovs", "Burovs"]` |
| 187 | Matīss Žuravļevs | `["Matīss Žuravļevs", "Matiss Zuravlevs", "Žuravļevs", "Zuravlevs", "Zuravleva", "Zuravlevam", "Zuravlevu"]` |

## B grupa — konvencijas pilnība, izmērīta raža 0

| pid | vārds | ierosinātās `name_forms` |
|---|---|---|
| 66 | Anda Čakša | `["Anda Čakša", "Anda Caksa", "Čakša", "Caksa", "Caksas", "Caksai", "Caksu"]` |
| 69 | Edvards Smiltēns | `["Edvards Smiltēns", "Edvards Smiltens", "Smiltēns", "Smiltens", "Smiltena", "Smiltenam", "Smiltenu"]` |
| 73 | Ināra Mūrniece | `["Ināra Mūrniece", "Inara Murniece", "Mūrniece", "Murniece", "Murnieces", "Murniecei", "Murnieci"]` |
| 75 | Juris Viļums | `["Juris Viļums", "Juris Vilums", "Viļums", "Vilums", "Viluma", "Vilumam", "Vilumu"]` |
| 169 | Didzis Kļuciņš *(inactive)* | `["Didzis Kļuciņš", "Didzis Klucins", "Kļuciņš", "Klucins", "Klucina", "Klucinam", "Klucinu"]` |
| 173 | Mārtiņš Štāls | `["Mārtiņš Štāls", "Martins Stals", "Štāls", "Stals", "Stala", "Stalam", "Stalu"]` |
| 176 | Gatis Madžiņš *(journalist)* | `["Gatis Madžiņš", "Gatis Madzins"]` |
| 180 | Jānis Tutins | `["Jānis Tutins", "Janis Tutins", "Tutins"]` |
| 181 | Aleksandrs Bartaševičs | `["Aleksandrs Bartaševičs", "Aleksandrs Bartasevics", "Bartaševičs", "Bartasevics", "Bartasevica", "Bartasevicam", "Bartasevicu"]` |
| 183 | Raivis Zeltīts | `["Raivis Zeltīts", "Raivis Zeltits", "Zeltīts", "Zeltits", "Zeltita", "Zeltitam", "Zeltitu"]` |
| 186 | Jānis Zalāns | `["Jānis Zalāns", "Janis Zalans", "Zalāns", "Zalans", "Zalana", "Zalanam", "Zalanu"]` |
| 194 | Neatkarīgā Rīta Avīze *(org)* | `["Neatkarīgā Rīta Avīze", "Neatkariga Rita Avize"]` |
| 196 | TV3 Ziņas *(org)* | `["TV3 Ziņas", "TV3 Zinas"]` |
| 244 | Katrīna Iļjinska *(journalist)* | `["Katrīna Iļjinska", "Katrina Iljinska"]` |

Žurnālistiem un organizācijām (176, 194, 196, 244) ierosinātas TIKAI pilnā vārda
formas: `relationship_type in ('journalist','organization')` liedz matcher-am
atvasināt kailo uzvārdu un locījumus (Seržanta precedents), un manuāli pievienota
kailā forma to aizsargu apietu.

## C grupa — nav ierosinājuma

| pid | vārds | kāpēc |
|---|---|---|
| 68, 70, 71, 72, 185, 182 | Judins, Augulis, Puntulis, Indriksone, Velps, Ozols | vārdā nav diakritikas — ASCII variants sakrīt ar esošo; pievienot nav ko |
| 198 | LTV De Facto | tāpat; «De Facto» kailā forma būtu kalks-substring, ne vārds |
| 200 | Krustpunktā | ASCII forma `Krustpunkta` ir tā paša raidījuma ģenitīvs un vienlaikus sugasvārda locījums; 190 korpusa trāpījumi ir `@Krustpunkta` handle, ko matcher jau ķer |
| 171, 172, 175, 177 | `@Heinrih5`, `@Tuksumsz`, `@Kurmitis_`, `@PStrautins` | `name` ir handle, ne personvārds; visi `inactive`. Formas nav ko būvēt — reāls uzdevums būtu identificēt personu, un tas ir atsevišķs lēmums |
| 174 | Toms Lūsis *(inactive)* | ASCII locījumi dotu `Lusi` (4 zīmes) — substring bumba pēc T1; **turklāt pastāvošs risks: matcher ŠODIEN jau ģenerē `Lūsi` un `Lūša`** (4 zīmes) no diakritikas formas. Atsevišķs operatora lēmums, ne šī saraksta daļa |

## Kolīziju priekšskats (≤4 zīmes un koplietoti uzvārdi)

- **Nevienā ierosinātajā formā nav ≤4 zīmju.** Īsākā ir `Caksu`/`Stala`/`Zalana` (5).
  `Lusi`/`Luša` apzināti izmesti (sk. C grupu).
- Koplietoti uzvārdi ierosinātajās rindās: `Judins` (2 nesēji) — bet 68 ir C grupā,
  formas nemainās. Pārējie ierosinātie uzvārdi korpusā ir unikāli
  `tracked_politicians` ietvaros.
- Katra ierosinātā ASCII kailā forma pārbaudīta pret visiem 89 649 dokumentiem;
  neviena netrāpa svešā vārdā (61 no 66 formām nedod nevienu trāpījumu vispār).
