# Claim-extractor prompta v3 — četri robi aizvērti un izmērīti — 2026-09-22

Iepriekšējie skrējieni (`claim-extractor-models-v2-2026-09-16.md`) nosauca trīs
konkrētus prompta robus un vienu kalibrācijas novirzi. Šis dokuments fiksē, kas
promptā mainīts un ko mērījums rāda pēc tam.

## Kas mainīts `.claude/agents/claim-extractor.md`

| # | Robs | Kur ierakstīts |
|---|---|---|
| 1 | **Rituāls ir žanrs, ne notikums.** Svinīgā sēdē teikta runa ar saturiskiem apgalvojumiem NAV apsveikums. Tests: izņem svētku ierāmējumu — vai paliek apgalvojums, ar ko var nepiekrist? | Step 3 «Skip these», aiz 2026-08-25 apsveikumu robežas |
| 2 | **`quote=null` → `confidence` ≤ 0.6**, bez izņēmuma | Confidence Calibration + Critical Rules 8 |
| 3 | **Nogriezts/paywall avots → `reasoning` sākas ar `NEEDS_REVIEW:`** — zemāka confidence viena pati nepietiek, jo triāža filtrē pēc `review_status`, ne pēc skaitļa | Critical Rules 8 |
| 4 | **Fragmentārs citāts: divi mehāniski testi** — (a) vai sākas teikuma sākumā (mazais burts = teikuma vidus, #20850), (b) vai noslēguma pieturzīme ir tieši tā, kas avotā | 6 jautājumu kontrolsaraksts, 4. jautājums |

Robi 1 un 3 nāca no v1/v2 secinājumiem; 2. no mērījuma, ka 4 no 7 modeļiem
pārsniedza griestus tieši trešās personas pārstāsta gadījumā; 4. no tā, ka
fragmentārais citāts atkārtojās trijās dažādās kārtās (08-12 A, 09-10 SWE-2,
09-16 Union Alpha).

## Jauns rīks: `scripts/eval_claim_extractor_score.py`

Līdz šim vērtēšana notika ar roku. Ar roku var pārbaudīt lēmumu, bet ne citāta
burtiskumu — tāpēc skripts dara mašīnas daļu: citāts kā **nepārtraukta
apakšvirkne** avotā, pieturzīmju klase atsevišķi, `quote=null` → conf ≤ 0.6,
nogriezts avots → `NEEDS_REVIEW`. Lēmumu pareizība paliek rubrikai.

**Validēts pret roku vērtētiem skrējieniem:** palaists pār visiem sešiem 09-16
raw failiem un atkārto publicēto tabulu (SWE-2 12/12 lēmumi + 1 forma;
DeepSeek/Kimi/Muse/Opus/Union Alpha 11/12 + 1 forma katram; GPT-5.6 Sol 10/12 + 2).

**Rīka paša kļūda, kas jāatceras:** pirmā versija noteica «nogriezts avots» pēc
atslēgvārdiem modeļa `reasoning` laukā un uzskatīja par defektu teikumu «avots
**nav** nogriezts paywall/stub» — atslēgvārds trāpīja noliegumā. Tā ir CLAUDE.md
**T16** klase paša rīka iekšienē. Labots: nogrieztību izlemj **avota teksts**.

## Mērījums pēc izmaiņām (tā pati v2 suite, tā pati komanda)

| Modelis | 09-16 (vecais prompts) | 09-22 (jaunais prompts) |
|---|---|---|
| **Opus** | 11/12 lēmumi (7. gad. ✗), 1 forma (conf 0.65) | **12/12 lēmumi, 0 formas** |
| **SWE-2 max (Devin CLI)** | 12/12 lēmumi, 1 forma (conf 0.75 pie `quote=null`) | **A: 12/12, 1 forma** (pieturzīme 8. gad.) · **B: 12/12, 0 formas** |
| DeepSeek v4.1-flash | 11/12 lēmumi, 1 forma (pieturzīme 8. gad.) | **12/12 lēmumi, 0 formas** |

Opus aizvēra **abus** savus iepriekšējos defektus vienā skrējienā: 7. gadījums
(ko tas atzīmēja tukšu) un conf griesti pie `quote=null`. Operatora lēmums
2026-09-22: **pastāvīgais panelis ir Opus + SWE-2**; DeepSeek rinda paliek kā
pierādījums, ka labojums ceļ arī lētāku modeli.

**Galvenais rezultāts — 7. gadījums.** Daudzrunātāju svinīgās sēdes raksts bija
suites diskriminators: 5 no 7 modeļiem to atzīmēja tukšu, kaut operators claim
glabāja (#703953). DeepSeek pēc 1. roba aizvēršanas to tagad ekstrahē pareizi.
Tas ir tiešs pierādījums, ka robeža bija prompta, ne modeļa trūkums.

**Confidence griesti turējās visos trijos jaunajos skrējienos** (iepriekš
pārkāpa Opus 0.65, SWE-2 0.75, Muse 0.7).

**Rituāla robeža nesabruka pretējā virzienā:** 1. gadījums (Ukrainas Neatkarības
dienas apsveikums) visos trijos skrējienos palika `empty`. Precizējums, ka runa
svinīgā sēdē ir pozīcija, nepadarīja apsveikumus par pozīcijām.

## Ko šis mērījums NEPIERĀDA

- **Divi skrējieni uz modeli joprojām ir plāni.** SWE-2 pieturzīmju defekts
  parādījās A skrējienā un pazuda B — tā ir variance, ne regresija, un tieši
  tāpēc vienam skrējienam nedrīkst ticēt kā novērtējumam.
- **Tēmas skripts nevērtē.** SWE-2 B skrējienā 2. gadījums aizgāja uz
  `Ārpolitika`, kamēr operatora labotā tēma ir `Aizsardzība un drošība`. Tēmas
  pareizība paliek roku pārbaude — skripts saka «lēmums OK», kaut tēma novirzās.
- **Union Alpha, Kimi, Muse un GPT-5.6 nav pārlaisti — apzināti.** Operatora
  lēmums 2026-09-22: panelis ir Opus + SWE-2, pārējās rindas paliek ar 09-16
  vērtībām kā vēsture. Tām divām, kas tomēr būtu bijušas informatīvas, ir arī
  vides šķērslis: `OPENROUTER_API_KEY` nav iestatīts, un Kimi Coding atslēga
  atbild **HTTP 403 «subscription does not have access to Kimi Code»** (pēdējais
  attiecas arī uz `hermes` noklusējuma modeli `kimi-k3` — atsevišķi risināms).
  Vājo modeļu vērtība šajā suitē bija tikai kā pierādījums, ka labojums ir
  prompta, ne modeļa nopelns; to jau dod DeepSeek rinda.

## Atkārtošanas recepte

Panelis: **Opus + SWE-2** (operatora lēmums 2026-09-22).

Pilnas komandas un pats uzdevuma prompts: **`docs/eval/prompt-golden-suite.md`**
(versionēts repo — sākotnēji tas dzīvoja `.scratch/`, kas ir gitignorēts un tiek
tīrīts, tātad recepte būtu sabrukusi klusi).

Devin CLI karogi un to slazdi: `wiki/operations/devin.md`.

Uzdevuma prompts nemainīts kopš 09-16 (sk. v2 dokumenta § «Jauna modeļa
pievienošana»); mainījies ir tikai pats aģenta fails, ko modelis izlasa.
