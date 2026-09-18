# Claim-extractor zelta kopa v2 — 5 modeļu salīdzinājums — 2026-09-16

## Uzbūve

Jauna 12 gadījumu suite (`claim-extractor-golden-cases-2026-09-16.md`, rubrika
nogriezta pirms padošanas → `_golden-2026-09-16-NO-RUBRIC.md`), uzbūvēta no
reālām produkcijas grūtībām kopš 2026-08-12: verdikti 2026-09-06, operatora
lēmumi 09-05 (ekonomikas dati / iestādes vērtējums vs operatīvs paziņojums),
09-15 («X stunda» simulācijas spēle), 08-22 (eksperta slots), 08-25 (biroja
balss, apsveikumi), 08-23 (trešās personas atstāsts), T6/daudzrunātāju klase.
Gaidāmie iznākumi = faktiskie operatora lēmumi (claim id katrā rubrikas rindā).

Palaišana identiska visiem: pašreizējais ražošanas prompts
`.claude/agents/claim-extractor.md`, dry-run, tas pats uzdevuma prompts,
modelim pašam jāizlasa abi faili.

| Modelis | Harness | Raw |
|---|---|---|
| Opus (C prompts) | `claude -p --model opus --allowedTools Read,Glob,Grep` | `_run-opus-2026-09-16.txt` |
| DeepSeek v4.1-flash | `hermes -p deepseek chat -Q --ignore-rules --max-turns 10` | `_run-deepseek-2026-09-16.txt` |
| SWE-2 max | `devin -p --model swe-2-max --permission-mode auto` | `_run-swe2-2026-09-16.txt` |
| Union Alpha (stealth, free) | `hermes chat -Q -m openrouter-union-alpha --ignore-rules` | `_run-union-alpha-2026-09-16-v2.txt` |
| Kimi k3 | `hermes chat -Q --ignore-rules --max-turns 10` | `_run-kimi-2026-09-16.txt` |
| GPT-5.6 Sol | `codex exec -m gpt-5.6-sol --sandbox read-only` | `_run-gpt56sol-2026-09-16.txt` |
| Muse Spark 1.3 Contributor (opencode free) | `hermes chat -Q -m opencode/muse-spark-1.3-contributor --ignore-rules` | `_run-muse-spark-2026-09-16.txt` |

## Rezultāts pa gadījumiem

| # | Tests | Opus | DeepSeek | SWE-2 | Union Alpha | Kimi k3 | GPT-5.6 Sol | Muse Spark 1.3 |
|---|---|---|---|---|---|---|---|---|
| 1 | Apsveikums bez instrumenta → empty | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 | Tēma seko instrumentam (Aizsardzība, ne Ārpolitika) | ✅ | ✅ | ✅⁽¹⁾ | ◐⁽²⁾ | ✅ | ◐⁽⁷⁾ | ✅ |
| 3 | Ekonomikas dati IR pozīcija (ne needs_review) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4 | Iestādes vērtējums regulējumam → extract | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 5 | Iestādes operatīvs paziņojums → empty | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 6 | Biroja balss (padomniece → LETA) → empty | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 7 | Daudzrunātāju sēde: tikai Mieriņas daļa → extract | ✗ | ✗ | ✅ | ✗ | ✗ | ✗ | ✅ |
| 8 | Eksperta slots (Slaidiņš) → extract | ✅ | ◐⁽³⁾ | ✅ | ✅ | ◐⁽³⁾ | ◐⁽³⁾ | ✅ |
| 9 | «X stunda» simulācija → empty | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 10 | mentioned ≠ runātājs (Dombrovskis) → empty | ✅ | ✅ | ✅ | ✅ | ✅ | ✗⁽⁸⁾ | ✅ |
| 11 | Noliegums + pretapgalvojums abas puses → extract | ✅ | ✅ | ✅⁽⁴⁾ | ✅ | ✅ | ◐⁽⁹⁾ | ✅ |
| 12 | Trešās personas atstāsts: quote=null, conf ≤0.6 | ◐⁽⁵⁾ | ✅ | ◐⁽⁵⁾ | ✅ | ◐⁽⁶⁾ | ◐⁽⁵⁾ | ◐⁽¹⁰⁾ |

⁽¹⁰⁾ Muse Spark nolēma needs_review, ne extract (produkcijā #689736 glabāts kā
extract); quote=null pareizi, conf 0.7.

⁽¹⁾ SWE-2 kodols pareizi (Aizsardzība), bet pārmērīgi sadala: otrs claim
«transatlantiskā vienotība darbos» ievietots Ārpolitikā — daļēji atceļ
operatora tēmas labojumu.
⁽²⁾ Union Alpha quote = teikuma FRAGMENTS («stronger NATO, 5% defence
investment…» — sākas vidustejumā), #20850 aizliegtā klase.
⁽³⁾ Citāts satura identisks, bet nomainīta noslēguma pieturzīme (avotā `,`/`!`
→ claimā `.`) — termināļa pieturzīmju klase (verdikti rindas 10/50).
⁽⁴⁾ SWE-2 sadala divos claims (Droni + Koalīcija un partijas), saturs pilns.
⁽⁵⁾ quote=null pareizi, bet conf virs 0.6 (Opus 0.65, SWE-2 0.75).
⁽⁶⁾ Kimi vispār nedeva confidence.
⁽⁷⁾ GPT-5.6 Sol pārmērīga fan-out: viens tvīts sadalīts 4 claims ar VIENU un to
pašu citātu 4 tēmās (Aizsardzība + Ukraina + Ārpolitika + Digitālā politika) —
T2 konsolidācijas pārkāpums; galvenā tēma pareiza.
⁽⁸⁾ GPT-5.6 Sol vienīgais ekstrahēja pozīciju `mentioned` politiķim no
žurnālista tvīta — stance piedēvē Dombrovskim 5 gadus vecu parafrāzi otrajā
rokā (quote=null, conf 0.6). Tieši talked-about klase, satura kļūda.
⁽⁹⁾ GPT-5.6 Sol stance satur tikai iepirkuma detaļas — nomesta gan nolieguma
puse («nekādi lādiņi netika aizmirsti»), gan pretapgalvojums premjeram par
dezinformāciju; tvīta asākā daļa pazudusi.

## Kopvērtējums

| Modelis | ✅ | ◐ | ✗ | Punkti |
|---|---|---|---|---|
| **SWE-2 max** | 11 | 1 | 0 | **11.5/12** |
| **Muse Spark 1.3 Contributor** | 11 | 1 | 0 | **11.5/12** |
| Opus (C) | 10 | 1 | 1 | 10.5/12 |
| DeepSeek v4.1-flash | 10 | 1 | 1 | 10.5/12 |
| Union Alpha | 10 | 1 | 1 | 10.5/12 |
| Kimi k3 | 9 | 2 | 1 | 10/12 |
| GPT-5.6 Sol | 6 | 4 | 2 | 8/12 |

Citātu verifikācija programmātiski pret avottekstu: 0 halucinētu citātu pie
neviens modelis; vienīgie verbatim pārkāpumi ir 3 termināļa pieturzīmes
(DeepSeek, Kimi, GPT-5.6 Sol — 8. gad.) un 1 fragmentārs citāts (Union Alpha —
2. gad.).

## Secinājumi

1. **9 no 12 gadījumiem vairs nešķir modeļus** — klases, kas 09-05/09-15 ierakstītas
   pašā promptā (ekonomikas dati, iestādes vērtējums/operatīvs, simulācijas
   spēle, biroja balss, apsveikumi), visi 7 izpilda pareizi. Prompta
   precedentu ierakstīšana strādā.
2. **7. gadījums (Mieriņa) ir suites galvenais discriminators: 5 no 7 saka
   empty.** Rubrika seko operatora faktiskajam lēmumam (#703953 glabāts kā
   pozīcija, verdikti rinda 7 to atstāja). Pareizi saņēma tikai SWE-2 un
   Muse Spark 1.3. Modeļi piemēro rituālo klasi
   («svinīgā sēde → ceremoniāls») plašāk nekā operators. Tas ir reāls
   prompta robs: 08-25 rituāla konvencijas un 09-06 daudzrunātāju precedenta
   robežlīnija promptā nav eksplicīti noformulēta. Ieteikums: apsvērt vienu
   prompta teikumu par svinīgo sēžu runām ar saturiskām konstatācijām.
3. **SWE-2 ir vienīgais, kas 7. gadījumu saņem pareizi**, tādēļ vadošais
   (11.5/12). Tā vienīgā ◐ ir conf kalibrācija (12. gad. 0.75 > 0.6).
4. **Union Alpha uz v2 ir strauji labāks nekā uz v1** (10.5/12 pret 8.5/11) —
   v1 zaudējumi galvenokārt bija klasēs, kas tagad ierakstītas promptā.
   Paliek fragmentārā citāta klase (2. gad.) — tā pati vājība kā v1 (10. gad.).
5. **Kimi k3 aizpilda v1 tukšo rindu**: v2 = 10/12, vājākās vietas — conf
   kalibrācijas forma (12. gad. bez confidence) un pieturzīme citātā (8. gad.).
6. DeepSeek v4.1-flash (10.5/12) praksē ekvivalents Opus šajā suite; tā v1
   profila pārmērīgā piesardzība (7. gad. v1) šeit parādās citur — 7. gadījuma
   empty, kur operators patur.
7. **GPT-5.6 Sol (Codex CLI) ir vājākais sešniecā (8/12).** Tā kļūdu profils
   atšķiras: nevis pārmērīga piesardzība, bet pārmērīga ekstrakcija — vienīgais
   modelis, kas ekstrahēja pozīciju `mentioned` politiķim no žurnālista tvīta
   (10. gad., satura ✗), un vienīgais ar 4-claim fan-out no viena tvīta (2. gad.).
   Claim-extractor lomai šis profils ir riskantāks nekā DeepSeek konservatīvais.
8. **Muse Spark 1.3 Contributor (opencode free) dala 1. vietu ar SWE-2
   (11.5/12)** — un ir pirmais bezmaksas modelis šajā līmenī. Vienīgā ◐ ir
   12. gadījuma needs_review-instead-of-extract (forma, ne saturs); citāti visi
   verbatim, neviena satura kļūda. Atruna: contributor variants = Meta drīkst
   trenēties uz promptiem (der tikai publiskam saturam; non-interactive
   apstiprinājums ieslēgts ar `security.allow_data_training_tiers_noninteractive`).

## Ātrums un tokeni (v2 skrējieni, 2026-09-16)

Avoti: Hermes sesiju DB (precīzi), Codex CLI pašuzskaite, Opus/SWE-2 — aptuveni
no raw failu birthtime→mtime (CLI tokenus nerāda).

| Modelis | Ilgums | Tokeni | Cena |
|---|---|---|---|---|
| GPT-5.6 Sol | ~217 s | 54,7 tūkst. kopā (Codex uzskaite) | — |
| Union Alpha | 254 s | 32k in (+82k cache) / 9,8k out | $0 (free) |
| Kimi k3 | 282 s | 40k in (+94k cache) / 7,1k out | $0 |
| Muse Spark 1.3 | 286 s | 36k in (+236k cache) / 9,0k out | $0 (opencode free) |
| Opus | ~340 s | nav datu | — |
| SWE-2 | ~592 s | nav datu | — |
| DeepSeek v4.1-flash | 925 s | 63k in (+241k cache) / 30k out (20k reasoning) | ~$0,028 |

DeepSeek ir lēnākais ar lielāko reasoning overhead (saskan ar 2026-09-08
secinājumu par 82 % reasoning īpatsvaru). Union Alpha — ātrs un bez maksas.

## Jauna modeļa pievienošana v2 suitei (recepte)

1. Saglabā raw: `docs/eval/_run-<modelis>-YYYY-MM-DD.txt` (gitignored).
2. Uzdevuma prompts (identisks visiem, maināms tikai fails, ja suite aug):

   > Tavi noteikumi ir failā `.claude/agents/claim-extractor.md` — izlasi to pilnībā. Tad izlasi `docs/eval/_golden-2026-09-16-NO-RUBRIC.md` (12 gadījumi) un izpildi tā instrukcijas: DRY-RUN, nekādu DB izsaukumu, nekādu citu failu lasīšanas. Atgriez TIKAI vienu JSON masīvu ar 12 objektiem secībā 1-12, katrs {"case": N, "decision": "extract"|"empty"|"needs_review", "claims": [{"topic","stance","quote","confidence","reasoning"}], "empty_reason": ...} — kā gadījumu fails prasa. Bez markdown apvalka.

3. Harness komandas (no repo saknes):
   - Hermes profils/modelis: `hermes chat --query-file <prompts> -Q [-m <modelis> | -p <profils>] --ignore-rules --max-turns 10 > docs/eval/_run-<m>-<datums>.txt 2>&1`
   - Claude: `cat <prompts> | claude -p --model opus --allowedTools "Read,Glob,Grep" > …`
   - Codex: `codex exec -m <modelis> --sandbox read-only "$(cat <prompts>)" > …`
   - Devin: `/e/Devin/bin/devin.cmd -p "$(cat <prompts>)" --model swe-2-max --respect-workspace-trust false --permission-mode auto > …`
4. Vērtēšana: parsē JSON masīvu (raw var beigties ar `session_id` astes rindu — griezt nost);
   katru citātu pārbaudīt programmātiski kā nepārtrauktu apakšvirkni pret
   `_golden-2026-09-16-NO-RUBRIC.md` (pieturzīmju maiņa = ◐ klase); vērtēt pret
   rubriku `claim-extractor-golden-cases-2026-09-16.md`; ◐ = 0.5.
5. Laiks/tokeni: Hermes → `state.db` `sessions` tabula (started_at/ended_at,
   input/output/cache/reasoning tokens); Codex → «tokens used» rinda; claude/devin
   → tikai failu timestampi.
6. Pievienot kolonnu šī faila tabulām + vienu secinājuma rindu.

## Metodikas piezīmes

- Viena suite, viena palaišana uz modeli — pierādījums par šo runu, ne stabils
  novērtējums. Rubrikas 7. gadījums balstīts operatora lēmumā, kas ir
  robežlēmums (4/5 modeļu konverģence uz empty to parāda); ja operators
  pārskata 7. gadījuma gaidāmo iznākumu, tabula jāpārrēķina (SWE-2 → 10.5,
  pārējie +1).
- ◐ = 0.5 kā v1 skalās. Termināļa pieturzīmes citātā vērtētas ◐ saskaņā ar
  verdiktu rindu 50 klasi (defekts, bet saturs identisks).
- DeepSeek raw beidzas ar `session_id` astes rindu (exit=1 no astes, JSON pats
  pilns — 12/12 parsēts).
- v1 (08-12, 11 gadījumi) rezultāti nav tieši salīdzināmi ar v2 — cits
  gadījumu kopums; v1 kalpo kā vēsturiskā bāzlīnija (Opus C 11/11, SWE-2 ~10,
  DeepSeek 9.5, Union Alpha 8.5).
