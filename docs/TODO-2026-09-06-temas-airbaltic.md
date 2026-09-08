# To-do: tēmu lapas un airBaltic sintēzes otrā daļa

Datums: 2026-09-06. Pamats: [HANDOFF-2026-09-06-temas-airbaltic.md](HANDOFF-2026-09-06-temas-airbaltic.md). Handoff apgalvojumi pārbaudīti pret kodu, DB (`data/atmina.db`, mērīts 2026-09-06) un wiki. Nekas vēl nav mainīts.

## Kas handoff dokumentā jālabo (pārbaudīts)

- **D punkts neattiecas uz šo vidi.** `.venv/Scripts/python.exe` = Python 3.12.10, `rg` ir PATH. Testus un renderu var palaist.
- **247 pret 254 nav kļūda.** 254 = visas `airBaltic` pozīcijas; 247 = bez 7 `relationship_type='inactive'` rindām. Vietne un wiki abi pareizi savā definīcijā. Klimats 19 = 19 (nav neaktīvo).
- **A3 ir plašāks, nekā rakstīts:** piesaiste nestrādā 8 no 9 sintēzēm, ne "pārsvarā". Tikai `airBaltic` sakrīt burtiski. Slugu→nosaukumu atrisinātāja repo nav (ir tikai `slugify()` vienā virzienā). `socialaa-politika` ir drukas kļūda; pareizais slugs `sociala-politika`.
- **Handoff nepamanīja gatavu specifikāciju:** `docs/research/2026-08-15-sintezu-kandidati.md` § 2 jau apraksta airBaltic otro nodaļu ar virsrakstu, avotu sarakstu un robežu "pēc Saeimas lēmuma" (lēmums bija 2026-08-20). Tās skaitļi novecojuši (204 → 254).
- **Balsojumu ķēdes ir garākas, nekā pirmā daļa citē.** 2026-04-16 par 953/Lm14 ir DIVI balsojumi (14:14 → 54/13/1/20; 15:53 → 49/23/1/15); raksts citē tikai otro. 2026-08-20 par 1495/Lp14 ir SEŠI balsojumi, un to `topic` ir `Budžets un finanses`, ne `airBaltic` — filtrs pēc tēmas tos nesatver, jāmeklē pēc `document_nr`.
- **Prognoze "nākamais balsojums pirms 31.08." piepildījās** (08-20). Pārējie divi pārskatīšanas kandidāti (ZZS "pa pusēm", pārvaldība vs finansējums) paliek nepārbaudīti.
- **Pretruna Nr. 24** ir `minor_shift`, `confirmed=1`, `reviewed=1` (claims 6628 ↔ 7414). Nepārklasificēt.

## A. Tēmu lapas — pirmā kārta (kods)

Faili: `src/render/topics.py`, `templates/tema.html.j2`, `src/render/syntheses.py`. Sagaidāms, ka `tests/test_render_chars.py` (SHA raksturojums) nokritīs — tas ir REGEN, ne regresija, ja diff ir tikai jaunās rindas.

- [ ] **A1 Arhīva saite.** Zem pozīciju saraksta (`LIMIT 15`, `topics.py:144-155`) pievienot "Skatīt visas N pozīcijas" → `pozicijas.html?tema=<encodeURIComponent(kanoniskais nosaukums)>`. `pzv1.js:429` salīdzina PRECĪZI ar kanonisko nosaukumu (ne slugu, reģistrjutīgi). N = direktorijas skaits (`topics.py:58-68`, tie paši nosacījumi). Teksts pielāgojas, ja N ≤ 15.
- [ ] **A2 `?tema=` uz profiliem.** Personu saitēm tēmas lapā pievienot to pašu parametru; `ppv1.js:199-206` to jau lasa un nezināmu tēmu klusi atmet uz "all". Pārbaudīt tēmas ar atstarpēm/diakritiku (`Budžets un finanses`, `Korupcija un KNAB`).
- [ ] **A3 Sintēžu piesaiste.** `topics.py:199-202` `name in s["topics"]`; `syntheses.py:176` nodod frontmatter bez normalizācijas. Risinājums: reversā karte `{slugify(n): n for n in TOPIC_GROUPS}` ielādes brīdī, pieņemt gan nosaukumu, gan slugu; neatpazītu vērtību rakstīt stderr (ne klusi izmest). Labot `socialaa-politika` → `sociala-politika` failā `wiki/synthesis/saeima-2026-04-30-balsojumi.md`. Pēc labojuma: visas 12 atšķirīgās vērtības atrisinās; pārbaudīt 9/9.
- [ ] **A3 tests.** `tests/test_topics.py` sauc `render_topics(syntheses=None)` — piesaiste netiek testēta. Pievienot testu, kas ar slug-formas frontmatter apstiprina piesaisti un nezināmai vērtībai — brīdinājumu. Mutācijas pārbaude: atgriežot reverso karti, testam jākrīt.
- [ ] **A4 Saistīto tēmu karte.** `topics.py:231` ņem 5 lielākās. Ieviest nelielu skaidru vārdnīcu (airBaltic → Transports, Valsts kapitālsabiedrības, Budžets un finanses; Klimats → Vide, Degviela un enerģētika, Lauksaimniecība), ar atkāpšanos uz esošo top-5, ja tēma kartē nav. Atslēgas validēt pret `TOPIC_GROUPS` testā.
- [ ] **A5 Etiķetes.** `tema.html.j2:33` "Top politiķi par tēmu" → "Visvairāk fiksēto pozīciju" (atlase ietver komentētājus); `topics.py:209` "Top politiķi" tāpat. Sintēžu kartītēm rādīt `created` (`tema.html.j2:101-110`, lauks jau ielādēts). "Nozīmīgums 0.50" (`pretruna-detail.html.j2:119`, `pretrunas.html.j2:110`) — vai nu paskaidrojošs teksts, vai noņemt no kartītes; lēmums operatoram. "Iepriekš/Pašlaik" loģika `enrich.py:239-245` ir pareiza pēc uzbūves; nemainīt bez konkrēta piemēra.
- [ ] **pmo.ee etiķete** — NAV jauns darbs. `topics.py:164` `_domain_from_url()` ir tā pati klase, ko jau apraksta `backlog/vietne-ui.md` § "[FIX] Avota etiķete rāda novirzītāja hostu". Ja labo, labo vienā piegājienā visām virsmām pēc tā ieraksta receptes (`documents.source_domain`), ne tikai tēmas lapai.
- [ ] **Vārti:** `bash scripts/check.sh`; renders `--only=topics` (vai atbilstošais domēns); pārlūka pārbaude plats + šaurs ekrāns ar airBaltic un Klimats; `@quality-reviewer` PASS; deploy tikai ar operatora apstiprinājumu.

## B. Produkta virziens — nav šīs kārtas darbs

Pierakstīt `backlog/vietne-ui.md` kā vienu [OPEN] ierakstu (direktorijas meklēšana/kārtošana, jautājumu salīdzinājums pa personām). Sasaistīt ar tur jau esošo "meklētājs neatrod tēmas („kurš runā par airBaltic?")". Neieviest bez operatora prioritātes.

## C. airBaltic sintēzes otrā daļa (redakcionāls darbs)

Datu bāze kopš 2026-04-22 (mērīts 2026-09-06): 139 pozīcijas (04: 14, 05: 15, 06: 7, 07: 28, **08: 66**, 09: 9; jaunākā 09-05), 7 spriedzes, 8 konteksta piezīmes, 16 dienas pārskati, 8 Saeimas balsojumi.

- [ ] **C0 Sākt no esošās specifikācijas** `docs/research/2026-08-15-sintezu-kandidati.md` § 2, ne no nulles. Tur ir virsraksta variants un avotu ID saraksts; skaitļus pārmērīt.
- [ ] **C1 Pirmās daļas audita tabula.** 10 pārbaudāmi apgalvojumi (sk. sub-aģenta tabulu nodošanā; galvenie: 23 PRET 16.04.; ZZS "pa pusēm" = Rokpelnis PAR / Augulis PRET; Valainis 07.04. ↔ 14.04.; Kulbergs "tālāk par Jāņiem neizvilks" 21.04.; prognoze pirms 31.08.). Katram: piepildījās / nepiepildījās / nav nosakāms + avots.
- [ ] **C2 ZZS "pa pusēm" — T6 pārbaude.** Frakcijas sadalījums TIEŠI balsojumā id 99 (`saeima_individual_votes.faction`), ne pēc `party`. Divi cilvēki nav "frakcija pa pusēm", ja frakcijā ir vairāk deputātu.
- [ ] **C3 Balsojumu ķēdes.** 953/Lm14 (2 balsojumi 04-16) un 1495/Lp14 (6 balsojumi 08-20: nod. kom. → steidzamība → 1. las. → priekšl. 2 (noraidīts 18/50) → priekšl. 3 → galīgais 54/21/1/7). Citēt ķēdi vai necitēt (T14). Konteksta piezīme #474 saka "ZZS balsoja pret" — pārbaudīt pret faction sadalījumu galīgajā balsojumā.
- [ ] **C4 Finansējuma instrumentu tabula ar PIRMAVOTIEM.** DB par 257 M / 25 % satur tikai politiķu izteikumus (#709018, #709046, #709060, #709071) — nevienu darījuma dokumentu. Pirms jebkura skaitļa tekstā: airBaltic paziņojums / Nasdaq Riga / MK protokols / obligacionāru sapulces (#468 min 08-17 kapitalizāciju). Kolonnas: summa, likme, termiņš, devējs, valsts daļa, stadija (piedāvāts / pilnvarots / noslēgts / izmaksāts).
- [ ] **C5 Personu līnijas pa laiku.** Kulbergs (08-20 aicinājums Saeimā, 08-21 14,5 % vērtējums — NE "vienā dienā", sk. quality-bars § Ierāmējuma vārti; 08-26 investors), Valainis (04-07 → 04-14 → 08-07 → 09-04 norobežošanās no 257 M), Švinka (04-16 atbildība → 08-20/21 kritika), Kozlovskis (07-20 #548462 "31.08. nav maināms" ↔ 08-14 #689616 "pagarināt līdz 31.12." — spec § 2 nosauc kā nepublicētu pavedienu; pārbaudīt, vai ir `contradictions` rinda, pirms saukt par maiņu). Amati un partijas uz notikuma brīdi.
- [ ] **C6 Melnraksts** `docs/drafts/airbaltic-2-…md` (mape jāizveido; `docs/` ir publiskā spogulī — bez operatora datiem). Frontmatter renderim: `title`, `description`, `created`, `politicians`, `topics` (pēc A3 līguma; kanoniskie nosaukumi). Hero: `output/atmina/images/synthesis/<slug>.png` pēc izvēles. Pirmajā daļā — īsa norāde uz turpinājumu, ne pārrakstīšana.
- [ ] **C7 Vārti pirms publicēšanas.** LV gramatika + stils; citāti burtiski; katram faktam saite; hronoloģija pret pirmavota datumu, ne `stated_at`; `@devils-advocate` pār visiem "mainīja nostāju" teikumiem; mobilais skats; operatora apstiprinājums. Melnraksts build kokā ≠ atļauja.

## Blakus atradumi (mazi, atsevišķi lēmumi)

- `wiki/operations/quality-bars.md` Ierāmējuma vārtu piezīme saka "visi trīs 1495/Lp14 balsojumi"; DB rāda sešus. Datums pareizs, skaits nē — viena vārda labojums.
- `quality-bars.md` nav sadaļas "Sintēze". Handoff uz to atsaucas kā uz sintēžu latiņu, bet tādas nav; C7 saraksts der par sākumu.
- Direktorijas pretrunu skaits (`topics.py:71-77`, bez join) un detaļas lapa (`:181-188`, INNER JOIN) var atšķirties, ja `opponent_id` ir orfāns. Šodien nav orfānu; pierakstīt, nelabot.
- `pzv1.js` lasa arī `q` parametru — handoff to nemin; noder direktorijas meklēšanai (B).
