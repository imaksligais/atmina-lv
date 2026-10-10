# Brief shared rules (daily + weekly)

Koplietotie žurnālistikas noteikumi `brief-writer` un `weekly-brief-writer`
aģentiem. Katrs aģents pievieno savu struktūras kontraktu; šie noteikumi ir
kopīgi.

## Mutācija
- Vienīgā atļautā DB rakstīšana ir `store_context_note()`. NEKAD DELETE/DROP/
  destruktīvs UPDATE uz `claims`, `contradictions`, `analyses`, `documents`,
  `document_politicians`, `tracked_politicians`, `saeima_*`.

## Avoti
- Katram pieminētam apgalvojumam jābūt `source_url`. Formāts: `[domēns.lv](pilns_url)`.
  Ja nav URL — `—`, nefabricē.

## Per-speaker atribūcija (OBLIGĀTI)
- Teikumā formā "X un Y [darbība] Z" katram nosauktajam runātājam DB jābūt
  vismaz vienam `claims` ierakstam par tieši TO substanci. Bucket-grupēšana un
  co-occurrence NAV pierādījums (2026-05-21 incidents: Lapsa par VK).

## NO DB iekšējiem ID/enum publiskā tekstā
- NEKAD `Pretruna #24`, `(minor_shift)`, `(6↔123)`. Lieto aprakstošas atsauces.

## LV-stilistika
- Pirms saglabāt palaid `lint_lv_style(content)` un izlabo visu. `5 %` (ar
  atstarpi), `eiro`, NE `ataka/polemika/aksi/startā`. Saglabā diakritiku.
- **Neizgudro vārdus / nelieto kalkus.** Lints (`src/lv_style.py` ANGLICISMS)
  noķer tikai slēgto sarakstu; PĀRI tam verificē pret standarta LV — kalkus
  lints NEvar noķert. Pazīstamie labojumi:

  | Nepareizi (kalks/izgudrots) | Pareizi (standarta LV) |
  |---|---|
  | ataka | uzbrukums *(lint)* |
  | polemika | diskusija / domstarpības *(lint)* |
  | melīšana | melošana *(lint)* |
  | konsenss | vienprātība / vienota nostāja *(lint)* |
  | smiltsstunda | smilšu pulkstenis *(kalks, NE lint)* |

  Vāciski kalkēti salikteņi (smiltsstunda, viesnīcgalds, lapsuvis) → aizvieto ar
  aprakstošu native frāzi. Arī `metaphor_hint` laukos: aprakstošas LV frāzes, ne
  kalki ("smiltsstunda" → "smilšu pulkstenis").

## Datumi un īpašvārdi
- Nedēļas dienu pie datuma raksti TIKAI pēc pārbaudes (`python -c "import
  datetime; print(datetime.date(2026,7,4).strftime('%A'))"`) — nepārbaudīta
  diena ir izdomāta diena (2026-07-05 weekly incidents: "ceturtdien,
  4. jūlijā" — patiesībā sestdiena).
- Personvārda pamatformu pirms locīšanas verificē pret avotu dokumentiem —
  divi līdzīgi vārdi lokās atšķirīgi (2026-07-05 incidents: "Elvja Strazdiņa"
  ← avotos dominē "Elviss", tātad ģen. "Elvisa").
- **Laika apgalvojums ir pārbaudāms fakts, ne stilistika** (2026-08-25): «vienā
  dienā», «tajā pašā dienā», «diennakts laikā», «nākamajā dienā» pirms rakstīšanas
  pārbaudi pret katra nosauktā politiķa claim `stated_at`. 2026-08-24 vakarā šī
  klase deva 3 instances no 3 mēģinājumiem, un trešo ieviesa pirmo divu labojums,
  tāpēc: pēc KATRA prozas labojuma pārlasi visu rindkopu, ne tikai laboto frāzi.
- **Spriedžu un piezīmju teksts pārskatā ir KOPIJA.** DB rindas labojums pēc
  pārskata uzrakstīšanas tajā neienāk pats — labo trīs vietās: DB rinda ·
  pārskata teksts (`context_notes`) · `wiki/dailies/` fails.

## Prozas bloku forma — palaga novēršana (2026-09-02)

Divi noteikumi. **A** noņem dublēto saturu, **B** sadala to, kas paliek.

**A — viena tēma, viens prozas bloks.** Dienas skelets konteksta kastītes ņem no
`routine_day_window(date)`, tātad TIKAI tās pašas dienas piezīmes
(`src/briefs.py::generate_daily_brief`). Kastīte pēc uzbūves vienmēr
stāsta par to pašu dienu, ko sintēzes rindkopa zem tabulas — dublēšanās ir
iebūvēta skeletā, ne aģenta kļūda. Tāpēc:

- Ja tēmai skeletā JAU IR `<div class="context-box">`, sintēzes rindkopu zem
  tabulas **neraksti no jauna**. Atļauts ir **viens** teikums, un tikai tad, ja
  tas pasaka to, kā kastītē nav (piem. kurš dienā klusēja, vai kā šodiena maina
  kastītes iezīmēto loku). Ja jaunā nav nekā — rindkopu izlaid pavisam.
- Ja tēmai kastītes NAV, sintēze ir 2–3 teikumi, kā līdz šim.
- Kastīti nekad nepārraksti un nesaīsini — tā paliek verbatim (sk. SAGLABĀ).

Etalons, kā to NEdarīt — pārskats 2026-09-01 § Imigrācija: 206 vārdu kastīte un
149 vārdu sintēze pēc kārtas, ar tiem pašiem aktieriem tajā pašā secībā un
gandrīz identisku noslēguma frāzi («nemainot nevienas puses deklarēto nostāju»).
Lasītājs pirms pirmās skenējamās rindas izlasīja 355 vārdus nepārtrauktas prozas.

**B — prozas bloks ir skenējams, ne virtene.** Attiecas uz KATRU prozas bloku,
ko raksti pats: tēmu sintēzēm, `## Nedēļas stāsts` rindkopām un konteksta
piezīmēm, ko raksti tāpēc, ka kastītes nav.

- **Maksimums 120 vārdu vienā blokā.** Pāri tam — dali.
- Ja blokā ir **4+ nosaukti aktieri**, tie iet sarakstā, ne semikolu virtenē:
  viens aktieris = viena rinda. Pieci vienas partijas politiķi vienā teikumā aiz
  domuzīmes ir tieši tā forma, ko šis noteikums aizliedz.
- Bloka pirmais teikums ir dienas būtība tajā tēmā (līdz ~25 vārdiem) un drīkst
  būt treknrakstā; detaļas seko zem tā.
- Saraksta rindas sākas ar `-`, nekad ar `N. ` (markdown `<ol>` slazds, sk. augstāk).

**Kopš 2026-09-02 abus sedz kods, ne tikai šis teksts.** `lint_lv_style()` 5. un
6. likums (`prose-block-too-long`, `context-box-synthesis-duplication`,
`src/lv_style.py`) nokrīt uz abiem pārkāpumiem; sliekšņi ir
`PROSE_BLOCK_MAX_WORDS = 120` un `SYNTHESIS_WITH_BOX_MAX_WORDS = 40`. Vārti
mutācijas-pārbaudīti pret 2026-09-01 pārskatu pirms un pēc labojuma: 5 atradumi
pret 0. Tas nozīmē, ka noteikuma pārkāpums vairs nav gaumes jautājums — pārskats
ar 200 vārdu rindkopu krīt lintā.

**Saucējs pašpārbaudē.** Ziņo trīs skaitļus: cik prozas bloku uzrakstīji, garākā
bloka vārdu skaits, cik bloku pārsniedza 120 vārdus. «Nav palaga» bez šiem trim
skaitļiem ir vārti, kas nevar nokrist.

## Neitralitāte
- Bez ieteikumiem, partijas perspektīvas, subjektīviem īpašības vārdiem.
  Proporcionāli substancei, ne mākslīgam balansam.
