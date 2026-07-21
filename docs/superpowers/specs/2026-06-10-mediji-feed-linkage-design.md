# Mediji ↔ feed-profilu savienojums — dizains

**Datums:** 2026-06-10
**Statuss:** apstiprināts brainstormā (pieeja A: hubs + sastāvdaļas)

## Problēma

Viens medijs šobrīd eksistē trīs nesavienotās sistēmās:

1. **`/mediji`** — 9 outleti no `sources.yaml` `outlets:` bloka (`src/outlets.py` → `src/render/mediji.py`): caurskatāmības fakti (īpašnieks, finansējums, juridiskā forma…) + web-rakstu pārklājums pa partijām.
2. **Profili → "Iestādes un mediji"** — 13 `tracked_politicians` rindas ar `relationship_type='organization'`, kas renderējas kā personas-profili (`politiki/<slug>.html`). Lielākoties X relay-feedi ar tukšām cilnēm ("0 pozīcijas, 0 laika līnija") un "Nav norādīts" galvenē; tiem blakus sēž ne-mediju organizācijas (Latvijas armija, LVM, LDDK).
3. **Wiki** — viena kaila rinda indeksā, bez lapas.

Pārklāšanās, ko datu modelis nezina (tas pats medijs abās sistēmās, bez saites):

| Medijs | Outlet (`/mediji`) | Feed-profili (`/politiki`) |
|---|---|---|
| LSM | `lsm` | LTV Ziņas (@ltvzinas), LTV Panorāma, LTV De Facto, Krustpunktā, Kas Notiek Latvijā |
| LETA | `leta` | LETA (@letanewslv) |
| NRA | `nra` | NRA (@nralv) |

Bez pāra: Delfi/Diena/Jauns/LA/Vēstnesis/TVNET (outleti bez feediem) un TV3 Ziņas/IR žurnāls/Saeimas ziņas (feedi bez outleta; Saeimas ziņas ir iestādes kanāls, ne medijs).

## Mērķa aina

Katrai virsmai viena skaidra loma: **/mediji = kas medijs ir** (caurskatāmība + pārklājums + tā X konti), **feed-profils = ko konkrētais konts publicē** (ar ceļu uz "māti"), **Profilu indekss = navigācija** (mediji atdalīti no iestādēm), **wiki = operatora skats**.

## 1. Datu modelis — savienojums dzīvo `sources.yaml`

Katrs outlet iegūst neobligātu `x_feeds:` sarakstu (X handle, bez `@`):

```yaml
- short_name: lsm
  ...
  x_feeds: [ltvzinas, ltvpanorama, ltvdefacto, Krustpunkta, KNL_LTV1]
- short_name: leta
  x_feeds: [letanewslv]
- short_name: nra
  x_feeds: [nralv]
```

- `src/outlets.py::load_outlets()` ekspozē `x_feeds: list[str]` (noklusējums `[]`).
- Render laikā join pret DB caur **`social_accounts.handle`** (autoritatīvais lauks; NE `tp.x_handle` — CLAUDE.md schema brīdinājums par kluso diverģenci), case-insensitive salīdzinājums → katram outletam saraksts `[(opponent_id, name, slug, publikāciju_skaits)]`.
- Nekādas DB migrācijas — tas pats config-driven princips, kas outletiem jau ir (nav outlets tabulas).
- Feed handle, kam DB-ā nav `social_accounts` rindas → izlaists ar stderr brīdinājumu (nevis kļūda) — spoguļo esošo "validation-level skip" stilu.

## 2. `mediji/<slug>.html` — sadaļa "X konti un raidījumi"

- Jauna sadaļa outlet detaļlapā (`medijs.html.j2`): kartīte per feed — logo (no `assets/photos/<feed-slug>.jpg`, ja ir; citādi iniciāļi tāpat kā personas kartēs), nosaukums, `@handle`, publikāciju skaits, saite uz `politiki/<feed-slug>.html`.
- **Vizuāli: tās pašas tumšās kartes kā CAURSKATĀMĪBA sadaļai** (lapas esošā kartīšu valoda) — kompaktākas, vienā rindā līdz 4. Nekādu jaunu komponenšu; sadaļas virsraksts tajā pašā uppercase-label stilā ("X KONTI UN RAIDĪJUMI").
- Outletiem bez feediem sadaļa nerādās vispār.
- Publikāciju skaits = `document_politicians` rindu skaits feed-profilam (tas pats avots, ko personas lapa rāda kā "publikācijas").

## 3. Feed-profils — outlet čips partijas slotā (ne banneris)

Profila galvenē partijas čips jau ir saite (`profile-party-tag` → `partijas/<slug>.html`); org-feediem tas šobrīd rāda fallback "Nav norādīts" (`politician.html.j2:47`). Outlets feedam IR viņa "partija":

- Organization-kind profiliem, kuru `social_accounts.handle` ir kāda outleta `x_feeds` sarakstā, partijas slots rāda **outlet nosaukumu kā saiti** uz `mediji/{outlet.slug}.html` — tieši tas pats vizuālais paterns, ko politiķim dod partijas saite.
- Nulle jaunu UI virsmu, nulle jauna CSS; "Nav norādīts" tukšums pazūd pats no sevis.
- Implementācija `src/render/politicians.py` (organization zars); outlet karte ielādēta vienreiz renderēšanas sākumā — bez N+1.

## 4. Profilu indekss — groza šķelšana "Mediji" / "Iestādes"

- `_persona_category` (src/render/_common.py) **paliek pure un nemainīta** — testi pie signatūras neplīst.
- Viens jauns helpers `_common.py::_split_org_category(category, pid, media_feed_ids)`:
  `category == "Iestādes un mediji"` un `pid ∈ media_feed_ids` → **"Mediji"**; citādi → **"Iestādes"**.
  Abi izsaucēji (`personas.py::_fetch_personas`, `search_index.py`) lieto šo helperi — loģika NAV dublēta divos failos. `media_feed_ids` = opponent_id kopa no visu outletu `x_feeds` join (1. sadaļa).
- Raila kanoniskā secība: Deputāti, Amatpersonas, Žurnālisti, Analītiķi, Ietekmētāji, **Mediji**, **Iestādes**, Citi.
- Kad railā izvēlēts "Mediji", zem kategorijas virsraksta viena saite **"Mediju caurskatāmība →"** uz `mediji.html` — vienīgais tilts no Profilu indeksa uz /mediji, viens `<a>` tags.
- sg-index (`search_index.py`): gan "Mediji", gan "Iestādes" kartējas uz `cat=2` — typeahead sekcija paliek apvienota ("Iestādes un mediji"); šķelšana ir tikai personas railā.
- Gaidāmais sadalījums pēc šķelšanas: Mediji ~9 feedi (LSM×5, LETA, NRA, TV3, IR), Iestādes ~4 (NBS, LVM, LDDK, Saeimas ziņas).
- **Priekšnoteikums:** TV3 un IR outleti (5. sadaļa) pievienoti PIRMS šķelšanas deploy — citādi to feedi kļūdaini nonāk "Iestādēs".

## 5. Divi jauni outleti: TV3 un IR

- `@outlet-researcher` palaišana katram (atsevišķi): TV3 (tv3.lv) un IR žurnāls (ir.lv).
- Aģents piedāvā sourced `outlets:` ierakstu; operatora review pirms commit (aģenta līgums to jau paredz).
- Pēc apstiprināšanas: `x_feeds: [TV3zinas]` un `x_feeds: [irLV]`.
- Hosti (tv3.lv, ir.lv), iespējams, nav scraper-avoti → `volume` var būt 0; tas ir pieņemami (precedents: Latvijas Vēstnesis ar 0 rakstiem).

## 6. Wiki — ģenerēta `mediji.md` (tikai no config, bez DB)

- `wiki_sync()` (patch `src/wiki.py` — NEKAD hand-edit regenerētos failus) indeksa kailo rindu aizstāj ar `[[mediji|Mediji]]` saiti un ģenerē `wiki/mediji.md`: tabula **tikai no `load_outlets()`** — outlet · tips · hosti · x_feeds. **Bez DB joiniem** (ne rakstu, ne publikāciju skaitu — tie dzīvo publiskajā lapā; wiki lapa ir konfigurācijas spogulis ~20 rindās koda).
- Lapa nonāk `wiki_sync` autoritatīvajā path-sarakstā (docstring).

## Kļūdu apstrāde

- `x_feeds` handle bez `social_accounts` rindas → skip + stderr brīdinājums.
- Viens handle divos outletos → pirmais uzvar + stderr brīdinājums (nav gaidīts datu stāvoklis).
- Outlet bez `x_feeds` → visas jaunās virsmas klusē (sadaļa/banneris nerādās); esošā uzvedība nemainās.

## Testi un verifikācija

- `tests/test_outlets.py` (vai esošais ekvivalents): `x_feeds` ekspozīcija, noklusējums `[]`, handle normalizācija.
- Mediji render: feed-sadaļa parādās LSM, neparādās Delfi.
- Politicians render: outlet saite partijas slotā LTV Ziņas profilā ("Latvijas Sabiedriskie mediji (LSM)" → `mediji/lsm.html`), NBS profilā paliek esošā uzvedība.
- Personas: kategoriju override (LTV Ziņas → Mediji, NBS → Iestādes); raila secība.
- `bash scripts/check.sh` zaļš (ruff + pytest + generate smoke).
- `wiki/CHANGELOG.md` ieraksts — šķelšana maina 2026-06-09 ieviesto "Iestādes un mediji" konvenciju.

## Ārpus tvēruma

- Feed-profilu likvidēšana / redirecti (pieeja B — noraidīta).
- Mediji indeksa kartīšu izmaiņas (feed skaits uz `mediji.html`) — YAGNI.
- Saeimas ziņas pārvietošana ārpus organization tipa — paliek "Iestādes", tas ir korekti.
