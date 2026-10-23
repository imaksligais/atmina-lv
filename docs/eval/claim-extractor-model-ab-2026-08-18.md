# Claim-extractor modeļu salīdzinājums uz golden suite — 2026-08-18

## Uzbūve

Tieši tas pats tests kā 2026-08-12 A/B/C eksperiments: 11 vēsturiski grūtie
gadījumi (`claim-extractor-golden-cases-2026-08-12.md`, rubrika nogriezta pirms
padošanas → `_golden-2026-08-12-NO-RUBRIC.md`), pašreizējais ražošanas prompts
`.claude/agents/claim-extractor.md` (variants C — 6 jautāumu kontrolsaraksts
Critical Rules 9. punktā). Dry-run, nekādu DB rakstīšanu.

Atšķirība no 08-12: skrien nevis Opus, bet **DeepSeek** (profils `deepseek`,
model.default=deepseek-v4-pro). Palaišana: `hermes -p deepseek chat -Q
--ignore-rules --max-turns 10` — aģents pats izlasa abus failus (prompts 56 KB >
Windows 32k arg limits). `--ignore-rules` = bez memory/skill injekcijas, vienādi
apstākļi abiem modeļiem. Raws: `docs/eval/_run-deepseek-2026-08-17.txt`.

**Kimi (kimi-k3) kārta neizdevās:** HTTP 429 "usage limit has been reached"
(00:43). Pārpalaist, kad limits atjaunojas — tad būs trīs modeļu salīdzinājums.

## Rezultāts pa gadījumiem (DeepSeek)

| # | DeepSeek | Vērtējums | Piezīmes |
|---|---|---|---|
| 1 | extract, quote verbatim, sarkasms izslēgts | ✅ | #7322 klase eksplicīti atpazīta reasoning; "tiem, kuri to vēlas" saglabāts |
| 2 | **empty** (paywall stubs) | ◐ | Rubrika gaida needs_review (operatora precedents #423 patur karotu claim). empty ir aizstājams, bet nav rubrikas iznākums |
| 3 | extract, abas puses, ķermeņa citāts ne virsraksts | ✅ | #113 klase pareizi; stance satur noliegumu + hibrīddraudus |
| 4 | needs_review, conf 0.4 | ✅ | Tekstbook #689420 klase: RT ar verbatim citātu ≠ first-party |
| 5 | empty | ✅ | Tā pati RT klase (#689422) — rubrika pieļauj empty |
| 6 | extract, viens konsolidēts claim | ✅ | "būtu jāveic" saglabāts kā modālis, nav pārspīlēts uz "pieprasa" (T2) |
| 7 | **empty** | ✗ | Sarkasms aizseguja reālu nostāju — operatora precedents #615828 patur claim ar atrunu. Rubrika: extract vai needs_review. Vienīgā reālā kļūda |
| 8 | extract, kondicionālis saglabāts | ✅ | "nevis atkal JV un Pro" iekšā; NVO apzīmējums apzināti NEpīts stance |
| 9 | extract, Valodu politika | ✅ | Tēma pēc rationale-principa; marķieru vārdu nav |
| 10 | extract, quote=null, conf 0.55 | ✅ | Precīzi B/C uzvedība: fragmentārie citāti noraidīti, hedži saglabāti (#20850) |
| 11 | empty, truncated fiksēts | ✅ | Rubrika pieļauj empty; paywall atzīmēts |

**Kopā: 9 ✅ + 1 ◐ + 1 ✗ ≈ 9.5/11**

## Salīdzinājums (tā pati suite, tā pati skala)

| Modelis / variants | Rezultāts |
|---|---|
| Opus A (bāzes prompts) | 8.5/11 |
| Opus B (kontrolsaraksts uzdevuma promptā) | 9.5/11 |
| Opus C (kontrolsaraksts aģenta failā — ražošanas prompts) | 11/11 |
| **DeepSeek (C prompts)** | **9.5/11** |
| Kimi k3 (C prompts) | nav — 429, pārpalaist |

## Secinājumi

1. **DeepSeek uz C prompta ≈ Opus B līmenis (9.5/11), zem Opus C (11/11).**
   Quote-fidelity klases (10., 11. gadījums), kuras kontrolsaraksts laboja
   Opus, DeepSeek izpilda pareizi — kontrolsaraksts pārnesas starp modeļiem.
2. **DeepSeek vājā vieta ir pretējā virzienā nekā gaidīts:** ne quote-fidelity,
   bet pārmērīga piesardzība — 7. gadījumā sarkastisks/indīgs tvīts tika
   atzīmēts empty, lai gan operatora precedents tajā patur pozīciju ar
   atribūcijas atrunu. Tas saskan ar 08-14 produkcijas testa profilu
   ("lietojams ar operatora QA"): DeepSeek drīzāk izlaiž nekā izgudro.
3. 2. gadījuma empty (ne needs_review) ir stila, ne satura novirze — paywall
   gate nostrādāja abos.
4. Praksē: DeepSeek kā claim-extractor paliek "pirmā atlase + operatora QA"
   lomā. Golden suite viņu nenokārtotu autonomijai, bet kļūdu profils ir
   konservatīvs (izlaisti > izgudroti), kas ir drošāk nekā halucinējošs
   ekstraktors.

## Metodikas piezīmes

- Viena uzraudzīta diena / viena suite ir pierādījums par šo runu, nevis
  stabils kvalitātes novērtējums (tāpat kā 08-14 secinājumos).
- Skaitīšana manuāli pret rubriku orkestratora kontekstā; raws fails saglabāts
  (`_run-deepseek-2026-08-17.txt`, 44 KB — satur arī modela darba pēdas).
- Kimi kārtai pārpalaist ar identisku komandu bez `-p deepseek`; sagaidāma
  `docs/eval/_run-kimi-2026-08-17.txt` aizstāšana (pašreizējā versija satur
  tikai 429 kļūdu).
