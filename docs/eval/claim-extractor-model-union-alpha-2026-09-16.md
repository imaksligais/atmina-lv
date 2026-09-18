# Claim-extractor golden suite — Union Alpha (OpenRouter stealth, free) — 2026-09-16

## Uzbūve

Tieši tā pati suite kā 2026-08-12 A/B/C, 2026-08-17 DeepSeek un 2026-09-10
SWE-2 skrējieniem: 11 vēsturiski grūtie gadījumi bez rubrikas
(`_golden-2026-08-12-NO-RUBRIC.md`), ražošanas prompts
`.claude/agents/claim-extractor.md`, dry-run (nekādu DB rakstīšanu), identisks
uzdevuma prompts kā DeepSeek 08-17 skrējienam.

Palaišana: `hermes chat --query-file … -Q -m openrouter-union-alpha
--ignore-rules --max-turns 10` (Hermes custom provider `openrouter-union-alpha`
→ OpenRouter `stealth/union-alpha`, bezmaksas, 262K konteksts).
`--ignore-rules` = bez memory/skill injekcijas, vienādi apstākļi. Raws:
`docs/eval/_run-union-alpha-2026-09-16.txt` (9 KB, gitignored kā visi `_run-*`).

**Prompta drift:** kopš DeepSeek skrējiena (08-17) prompts ir +19 rindas
(09-05/06 komiti), kopš SWE-2 skrējiena (09-10) vēl «X stunda» klase
(09-15, 9f1187b4). Salīdzinājums ir virziena, ne precīzs.

## Rezultāts pa gadījumiem (Union Alpha)

| # | Union Alpha | Vērtējums | Piezīmes |
|---|---|---|---|
| 1 | extract, quote verbatim, sarkasms izslēgts | ✅ | "tiem, kuri to vēlas" saglabāts; pēdējās sarkastiskās rindas nav stance (#7322 klase reasoning) |
| 2 | **empty** (paywall stubs) | ◐ | Rubrika gaida needs_review. Tā pati novirze kā DeepSeek (08-17) — empty ir aizstājams, bet nav rubrikas iznākums |
| 3 | extract, abas puses, ķermeņa citāts | ✅ | Virsraksts nav quote; noliegums + hibrīddraudi abi stance; verbatim ministres teikums (#113 klase) |
| 4 | needs_review, conf 0.6, marķieris reasoning | ✅ | RT-verbatim klase (#689420) atpazīta ar eksplicītu NEEDS_REVIEW — formas disciplīna labāka nekā SWE-2 |
| 5 | needs_review, conf 0.65, marķieris | ✅ | Tā pati klase (#689422); rubrika pieļauj |
| 6 | extract, viens konsolidēts claim | ✅ | "būtu jāveic" saglabāts kā aicinājums, ne prasība (T2) |
| 7 | extract, "diskotēkām" saglabāts, atruna "viņas formulējumā" | ◐ | Platums un atribūcija ideāli (#615828). BET tēma `Sociālā politika`, ne `Imigrācija` pēc operatora lēmuma 2026-08-03 — tā pati novirze kā Opus B (NVO) un SWE-2 (NVO) |
| 8 | extract, kondicionālis ZAUDĒTS | ◐ | Stance pārveidots par ieteikumu ("būtu vajadzīgi radikālāki sabiedrotie nekā JV un Pro"); rubrika prasa saglabāt "ja atkal JV un Pro" kondicionāli. RB/NVO pareizi nav atsevišķs claim |
| 9 | extract, Valodu politika, kondicionālis saglabāts | ✅ | "var dzīvot tikai tad, ja" iekšā; marķiera vārdi nav noplūduši |
| 10 | extract, hedži saglabāti, bet **fragmentārs citāts** | ◐ | Quote = `klimata jautājumi, iespējams, uz kādu brīdi "jāiepauzē"` — verbatim nepārtraukts, bet TEIKUMA FRAGMENTS, tieši #20850 aizliegtā klase (tā pati kļūda kā SWE-2 09-10) |
| 11 | extract (bez needs_review), Tūtina klase atpazīta, conf 0.55 | ◐ | Institūcijas balss pareizi; paywall fiksēts; verbatim citāts. BET trūkst NEEDS_REVIEW marķiera truncated-source ekstrakcijai — tā pati forma-kļūda kā SWE-2 |

**Kopā: 6 ✅ + 5 ◐ + 0 ✗ = 8.5/11**

Visi 10 citāti programmātiski pārbaudīti pret avottekstu: visi verbatim
nepārtraukti (0 halucinētu/izgudrotu citātu).

## Salīdzinājums (tā pati suite, tā pati skala)

| Modelis / variants | Prompts | Rezultāts |
|---|---|---|
| Opus A (bāzes prompts, 08-12) | A | 8.5/11 |
| Opus B (kontrolsaraksts uzdevumā, 08-12) | B | 9.5/11 |
| Opus C (kontrolsaraksts aģenta failā, 08-12) | C | 11/11 |
| DeepSeek v4-pro (08-17) | C | 9.5/11 |
| SWE-2 max, Devin CLI (09-10) | C + 09-05/06 | ≈10/11 |
| **Union Alpha, OpenRouter (09-16)** | **C + 09-05/06 + 09-15** | **8.5/11** |
| Kimi k3 (08-17) | C | joprojām nav — 08-17 kārts 429 |

## Secinājumi

1. **Union Alpha = Opus A līmenis (8.5/11), zem DeepSeek (9.5) un SWE-2 (~10).**
   Kļūdu profils: neviens ✗ (nekādu invertētu nostāju, izgudrotu vai
   halucinētu citātu — visi 10 citāti verbatim pārbaudīti), bet 5 ◐ formas /
   rubrikas-gate līmenī.
2. **Divas atkārtotas klases saglabājas visos ne-Opus-C modeļos:** 2. gadījuma
   empty-instead-of-needs_review (kā DeepSeek) un 10. gadījuma fragmentārais
   citāts #20850 (kā SWE-2). 7. gadījuma tēmas novirze (ne Imigrācija) tagad
   novērota jau pie 4 modeļiem (Opus B, SWE-2, Union Alpha — DeepSeek to gadījumu
   zaudēja citādi, empty ✗).
3. **Unikālā Union Alpha kļūda:** 8. gadījuma kondicionāļa zudums — stance
   pārveidots no "ja atkal JV un Pro, tad vezums nekur nekustēsies" par
   ieteikuma formu. Ne DeepSeek, ne SWE-2 to nepieļāva.
4. **Pret DeepSeek:** DeepSeek zaudēja uz pārmērīgas piesardzības (7. gad. empty
   = vienīgā reālā ✗); Union Alpha nav pārmērīgi piesardzīgs (ekstrahē visur,
   kur vajag), bet zaudē uz formas disciplīnas. Praksē DeepSeek profils
   (izlaiž > izgudro) atmina pipeline ir drošāks.
5. Prakse: Union Alpha (bezmaksas, 262K) der kā eksperimentu/otrā viedokļa
   modelis, bet claim-extractor "pirmās atlases" lomai pašlaik vājāks par
   DeepSeek — 5 formas/gate ◐ nozīmē, ka operators QA posmā noķertu vairāk
   nekā ar DeepSeek.

## Metodikas piezīmes

- Viena suite ir pierādījums par šo runu, nevis stabils novērtējums.
- Skaitīšana manuāli pret rubriku orkestratora kontekstā; ◐ = 0.5, saskaņā ar
  08-12/08-18/09-10 skalām (fragmentārais citāts 10. gadījumā vērtēts ◐ tāpat
  kā SWE-2 identiskai uzvedībai; 2. gad. empty vērtēts ◐ tāpat kā DeepSeek).
- Prompta drift (+19 rindas pret DeepSeek, +«X stunda» klase pret SWE-2)
  nozīmē, ka 8.5 vs 9.5 vs 10 nav tīrs modeļa salīdzinājums; precīzam
  pār-testam visus trīs būtu jāpārlaiž uz pašreizējā prompta.
- Kimi k3 rinda tabulā joprojām tukša.
