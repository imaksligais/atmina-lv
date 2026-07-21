# Solījumu kartes lapas uzlabojumi + X raksta pārstrukturēšana (2026-07-09)

**Statuss:** apstiprināts (operators izvēlējās "A + B kopā" + X raksta pārstrukturēšanu).
**Datu verifikācija:** visi sintēzes un X raksta skaitļi pārbaudīti pret DB
(`claim_type='program_promise'`, 276 rindas) 2026-07-09 — viss sakrīt; X rakstā
divas precizējamas vietas (sk. § X raksts).

## Problēma

Sintēzes lapa ir ~7 400 px prozas bez navigācijas; kvantificēto solījumu tabula
(513 px) mobilajā pārplūst pāri `.post-content` (348 px) bez scroll-ietinuma →
horizontāla visas lapas ritināšana un nogriezta pēdējā kolonna. Vizuālākais
saturs (polarizācijas asis, "X no 14" skaiti) ir tikai rindkopās.

## Arhitektūras ierobežojums

Sintēžu markdown iet caur `bleach` balto sarakstu (`_sanitize_html`) — nav
`div`/`span`/`class`/`script`. Interaktivitāte ienākama tikai (a) ģeneriski
šablona/CSS līmenī vai (b) ar uzticamu vidžetu injekciju PĒC sanitizācijas.

## A — Ģeneriskie uzlabojumi (visas sintēzes, tagad un nākotnē)

`src/render/syntheses.py`: jauns post-sanitize solis `_enhance_synthesis_html()`:

1. **Tabulu scroll-ietinums:** katru `<table>` ietin `<div class="table-scroll">`
   (CSS: `overflow-x: auto`). Salabo mobilās pārplūšanas bugu.
2. **Tukšo šūnu pieklusināšana:** `<td>—</td>` → `<td class="cell-empty">—</td>`.
3. **Satura rādītājs:** h2 virsrakstiem pievieno `id` (slugify), un ja lapā ≥3 h2,
   šablons (`blog-post.html.j2`) renderē "Saturs" enkuru bloku pirms satura.
   CSS `scroll-margin-top` kompensē lipīgo nav.

Drošība: transformācijas notiek pēc sanitizācijas, bet ievade tām ir jau
sanitizēts HTML + pašu ģenerēti id/klases — uzticamības modelis nemainās.

## B — Vidžetu injekcija

**Mehānisms:** markdown rindkopa, kas satur tieši `[vidžets:NAME]`, pēc
sanitizācijas (`<p>[vidžets:NAME]</p>`) tiek aizstāta ar faila
`wiki/synthesis/widgets/<slug>/<NAME>.html` saturu **bez** sanitizācijas —
vidžetu faili ir repo autorēti un uzticami tāpat kā šabloni. Trūkstošs fails →
marķieri izmet + `logger.warning` (renderis nekrīt). Testi `tests/test_load_syntheses.py`.

**Vidžeti šai lapai** (`wiki/synthesis/widgets/partiju-programmas-2026-solijumu-karte/`),
CSS klašu telpa `.syn-w*`, abas tēmas (gaišā default + tumšā), partiju krāsas
caur `--party-color` konvenciju:

| Fails | Saturs |
|---|---|
| `saraksti.html` | 14 sarakstu rindas: īsvārda čips, saite uz CVK programmu, pozīciju skaita mini-josla (max 25), statusa čips (koalīcija / opozīcija / ārpus Saeimas) |
| `solijumu-matrica.html` | 31 tēma × 14 saraksti pārklājuma matrica; aizpildīta šūna = saite uz partijas lapas "Programma" sadaļu; sticky galvene + pirmā kolonna; scroll konteinerī. ĢENERĒTS ar `scripts/build_solijumu_matrica.py` no DB — commitēts artefakts, pārģenerē manuāli, ja programmas mainās |
| `ass-krievija.html` | Spektrs: Pārraut saites [ASL, NA] · Atbalsts Ukrainai [JV, LA, AS, ZZS, JKP; LPV šaurāks] · Starppozīcija [SC] · Neitralitāte/neiesaistīšanās [GS, SV-AJ, ST] · Nemin [MMN, PRO] |
| `ass-valoda.html` | Stingrāks valsts valodas režīms [ASL, NA, JKP, JV] · Cits virziens [LPV — angļu val. biznesam] · Plašākas mazākumtautību valodu tiesības [ST, SV-AJ, SC] · Atsevišķas pozīcijas nav [AS, GS, LA, MMN, PRO, ZZS] |
| `ass-gimene.html` | Laulību vienlīdzība [PRO] · Apiet (tikai naudas atbalsts) [AS, JV, JKP, LA, MMN, NA, SC, ST, ZZS] · Pret Stambulas konvenciju / tradicionālā definīcija [LPV, SV-AJ, ASL, GS] |
| `ass-zalais.html` | Klimatneitralitāte [PRO] · Pārskatīt/pakārtot konkurētspējai [AS, ZZS, MMN, NA, LA] · Atteikties [SV-AJ] · Nemin [ASL, GS, JKP, JV, LPV, SC, ST] |
| `konsensa-joslas.html` | 14 punktu joslas: veselības pieejamība 14 · birokrātija 13 · rindas tieši 11 · imigrācijas pozīcija 11 · pedagogu atalgojums 9 · tiešmaksājumi 8 |
| `modes-joslas.html` | NĪN atcelšana 8/14 ar čipiem [ASL, GS, JKP, LPV, MMN, ST, ZZS, SV-AJ] + piezīme "JV — pretējais virziens"; pensiju 2. līmenis 7/14 ar čipiem [ASL, GS, JKP, LPV, MMN, NA, SV-AJ] |
| `klusesanas-joslas.html` | klimats 7 · Rail Baltica pozīcija 7 · ES politika 6 · digitālā politika 5 · sabiedriskie mediji 5 · partiju finansēšana 2 |

**Marķieru izvietojums** `wiki/synthesis/partiju-programmas-2026-solijumu-karte.md`
(manuāla satura rediģēšana, LV gramatikas vārti):

- Konteksta tabulu aizstāj `[vidžets:saraksti]`
- Jauna sadaļa "## Karte: kurš par ko runā" pēc Konteksta ar `[vidžets:solijumu-matrica]`
- Pēc konsensa bullet saraksta `[vidžets:konsensa-joslas]`
- Pēc "Divi solījumu tipi" bullet saraksta `[vidžets:modes-joslas]`
- Katras polarizācijas apakšsadaļas sākumā attiecīgais ass vidžets
- Pēc klusēšanas zonu saraksta `[vidžets:klusesanas-joslas]`

## X raksts (`docs/social/2026-07-09-partiju-programmas-x-article.md`)

1. Treknraksta rindkopu ievadi → `##` virsraksti (X Articles atbalsta headerus)
2. Stat-rinda pēc āķa rindkopas: "14 saraksti · 276 pozīcijas · 31 tēma"
3. Precizitāte: "zelta rezerves glabāšanā Rīgā" → "zelta krājumus glabāšanā
   Latvijas Bankā" (tā DB klaimā); "270 dienu nodokļu brīvdienas" → "270 dienu
   **atliktas** nodokļu brīvdienas"
4. Noslēguma rindas slīpējums
5. Piezīme operatoram: otrs iekšējais attēls = Krievijas ass vidžeta PNG
   eksports (ekrānuzņēmums, 16:9) pie sadaļas "Dziļākā plaisa"

## Verifikācija

`bash scripts/check.sh` (ruff + pytest + smoke) · lokāls renderis
`--only=sintezes` · Playwright ekrānuzņēmumi (desktop + 390 px mobilais, abas
tēmas) · horizontālās ritināšanas pārbaude mobilajā. Deploy TIKAI ar operatora
apstiprinājumu (publish pause).
