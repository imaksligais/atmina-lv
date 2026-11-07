# Claim-extractor golden suite — SWE-2 (Devin CLI) — 2026-09-10

## Uzbūve

Tieši tā pati suite kā 2026-08-12 A/B/C un 2026-08-18 DeepSeek/Kimi skrējieniem:
11 vēsturiski grūtie gadījumi bez rubrikas (`_golden-2026-08-12-NO-RUBRIC.md`),
ražošanas prompts `.claude/agents/claim-extractor.md`, dry-run (nekādu DB
rakstīšanu), identisks uzdevuma prompts kā 08-17 skrējieniem.

Atšķirības no DeepSeek skrējiena (08-17):

1. **Prompts ir mainījies.** Kopš 08-17 `claim-extractor.md` ir +19 rindas
   (2026-09-05/06 komiti: ekstrakcijas precedenti promptā, review_status
   trigera faktu labojumi). SWE-2 skrēja ar nedaudz spēcīgāku promptu nekā
   DeepSeek 9.5/11 skrējienā — salīdzinājums ir virziena, ne precīzs.
2. **Harness cits:** `devin -p` (Windsurf harness, modelis `swe-2-max`,
   `--permission-mode auto` = tikai read-only, `--respect-workspace-trust false`)
   Hermes `--ignore-rules` vietā. Devin var injektēt savus workspace noteikumus;
   abos gadījumos aģents pats izlasa tos pašus divus failus.
3. Raws: `docs/eval/_run-swe2-2026-09-10.txt` (12 KB). Repo netika rakstīts
   (pārbaudīts ar git status / failu mtimes).

## Rezultāts pa gadījumiem (SWE-2 max)

| # | SWE-2 | Vērtējums | Piezīmes |
|---|---|---|---|
| 1 | extract, quote verbatim, sarkasms izslēgts | ✅ | #7322 klase eksplicīti reasoning; "tiem, kuri to vēlas" saglabāts; Lietuvas modeļa robeža iekšā |
| 2 | **extract**, quote=null, conf 0.55 | ◐ | Rubrika gaida needs_review. Satura vārti izpildīti (quote=null, conf ≤0.6, paywall fiksēts reasoning), bet trūkst NEEDS_REVIEW marķiera — triāžas rindā claim neparādītos. Tēma pareizi `Aizsardzība un drošība` (vēsturiskais #423), kur A/B/C visi novirzījās uz Ārpolitika |
| 3 | extract, abas puses, ķermeņa citāts | ✅ | Virsraksts nav quote; noliegums + hibrīddraudi abi stance; verbatim ministres teikums (#113 klase) |
| 4 | needs_review, conf 0.5 | ✅ | Tekstbook #689420 klase ar eksplicītu precedentu reasoning |
| 5 | needs_review, conf 0.5 | ✅ | #689422 klase atpazīta; rubrika pieļauj abus |
| 6 | extract, viens konsolidēts claim | ✅ | "būtu jāveic" → aicina, ne pieprasa (T2). Piezīme: apgalvojums par Straumes laika 90 miljoniem transportēts stance kā fons — C varianta papildu piesardzība (nepārbaudīti apgalvojumi par nosauktu personu) šeit nenostrādā, bet tas nav rubrikas PASS kritērijs |
| 7 | extract, "diskotēkām" saglabāts, atruna "ko viņa raksturo kā" | ◐ | Platums un atribūcijas atruna — ideāli (#615828). BET tēma `NVO un pilsoniskā sabiedrība`, ne `Imigrācija` pēc operatora lēmuma 2026-08-03 (stated-rationale princips) — tā pati novirze, ko 08-12 pieļāva variants B |
| 8 | extract, kondicionālis saglabāts | ✅ | "ja atkal JV un Pro" iekšā; RB/NVO nav atsevišķs claim |
| 9 | extract, Valodu politika | ✅ | Kondicionālis saglabāts; marķiera vārdi reasoning nav noplūduši |
| 10 | extract, 2 claims dažādās tēmās, hedži saglabāti | ◐ | **Klimata claim quote = "varbūt necensties vienmēr būt pirmrindiekiem, izdabājot Briselei" — fragmentārs citāts, tieši #20850 / A-varianta aizliegtā klase.** Enerģētikas claim quote korekts. Kontrolsaraksta 4. punkts (verbatim NEPĀRTRAUKTS) šeit nenostrādāja |
| 11 | extract, institūcijas balss atpazīta, verbatim quote, conf 0.6 | ◐ | Tūtina klase (#555829) pareizi; paywall fiksēts reasoning. BET atkal trūkst NEEDS_REVIEW: truncated-source marķiera, ko Step 2 gate prasa ekstrakcijai no stubs |

**Kopā: 8 ✅ + 4 ◐ + 0 ✗ ≈ 10/11**

## Salīdzinājums (tā pati suite, tā pati skala)

| Modelis / variants | Prompts | Rezultāts |
|---|---|---|
| Opus A (bāzes prompts, 08-12) | A | 8.5/11 |
| Opus B (kontrolsaraksts uzdevumā, 08-12) | B | 9.5/11 |
| Opus C (kontrolsaraksts aģenta failā, 08-12) | C | 11/11 |
| DeepSeek v4-pro (08-17) | C | 9.5/11 |
| **SWE-2 max, Devin CLI (09-10)** | **C + 09-05/06 papildinājumi** | **≈10/11** |
| Kimi k3 (08-17) | C | joprojām nav — 08-17 kārta beidzās ar 429 |

## Secinājumi

1. **SWE-2 ir spēcīgākais ne-Opus rezultāts šajā suite un vienīgais bez cietām
   kļūdām (0 ✗).** Neviena invertēta nostāja, neviens izgudrots vai paplašināts
   apgalvojums, neviens halucinēts citāts/URL. Visas četras zaudētās puspunktu
   vietas ir formas/gate līmenī, ne satura.
2. **Vājā vieta ir marķiera disciplīna, ne piesardzība** — pretēji DeepSeek
   (kura vienīgā reālā kļūda bija pārmērīga piesardzība, empty 7. gadījumā).
   SWE-2 divās paywall/stub situācijās (2., 11.) saturu apstrādā pareizi, bet
   neuzliek obligāto `NEEDS_REVIEW:` marķieri — claims apietu @quality-reviewer
   triāžu. Tas ir fixable ar vienu prompta teikumu, ja SWE-2 kādu dienu liktu
   ražošanā.
3. **Fragmentāro citātu klase (#20850) paliek dzīva** — 10. gadījuma Klimata
   quote ir burtiski tā pati kļūda, ko 08-12 pieļāva variants A. 6 jautājumu
   kontrolsaraksta 4. punkts to Opus C nosedza, SWE-2 — nē.
4. Tēmas-rationale novirze 7. gadījumā (NVO, ne Imigrācija) atkārto Opus B
   novirzi; operatora precedents 2026-08-03 acīmredzami nav pietiekami
   izceļots pašā promptā neviem harness/modelim, izņemot C ar kontrolsarakstu.
5. Praksē: SWE-2 (bezmaksas līmenis, 262K konteksts) ir derīgs claim-extractor
   "pirmā atlase + operatora QA" lomai ar kļūdu profilu, kas šajā suite ir
   tuvāk Opus C nekā DeepSeek — ar vienu konkrētu uzraudzības punktu:
   pārbaudīt NEEDS_REVIEW marķieru klātbūtni visos paywall/truncated claims.

## Metodikas piezīmes

- Viena suite ir pierādījums par šo runu, nevis stabils novērtējums (tāpat kā
  08-12/08-14/08-18 secinājumos).
- Skaitīšana manuāli pret rubriku orkestratora kontekstā; ◐ skaitās 0.5,
  saskaņā ar 08-12/08-18 skalām (A fragmentārais citāts 10. gadījumā toreiz
  tika vērtēts ◐ — SWE-2 identiskai uzvedībai tiek tas pats).
- Prompta drift (+19 rindas kopš DeepSeek skrējiena) nozīmē, ka 10 vs 9.5
  nav tīrs modeļa salīdzinājums; precīzam pār-testam DeepSeek būtu jāpārlaiž
  uz pašreizējā prompta.
- Kimi k3 rinda tabulā joprojām tukša — pārpalaist ar identisko komandu, kad
  ir jēga papildināt salīdzinājumu.
