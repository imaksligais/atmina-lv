# Saeimas pusloks — dizains (2026-10-08)

**Ideja:** `docs/plans/2026-10-07-saeimas-pusloks-ideja.md`. **Ceļš:** arhitektūras (jauna lapa + jauns JS asset). Operators deleģēja atvērtos jautājumus; lēmumi zemāk pieņemti kopā ar advisor un gaida operatora pārskatu.

## Mērķis

Viena lapa, kurā uzreiz redzams, KAS ievēlēts 15. Saeimā, un ar vienu klikšķi — ko katrs no viņiem DARA UN SAKA mūsu datos. Veiksme: lasītājs telefonā atrod jebkuru deputātu ≤2 pieskārienos, un katra krāsa saka, ko tā skaita un par kādu periodu.

## Fakti (mērīti 2026-10-08)

- `data/cvk_sv2026_ievēlētie.yaml` — 100 vārdi, komitēts, PROVIZORISKS CVK aprēķins; to jau lasa `src/render/personas.py` (precīza vārda sakritība). Oficiālā CVK lapa `dati.cvk.lv/SV2026/ieveletie-deputati/` — 404. `Saeima15_DepWeb_Public` — 0 ierakstu.
- No 100 ievēlētajiem 98 ir `tracked_politicians` pēc precīza vārda (kohorta seedēta); bez profila: Gita Plaude, Leontijs Morozs. 41 no 100 balsoja 14. Saeimā.
- `data/cvk_sv2026_rezultati.yaml` nes sarakstu vietas; `parties.color` un `short_name` jau lieto `partijas.html` vēlēšanu bloks.
- `saeima_individual_votes`: 139 atšķirīgi 14. Saeimas balsotāji, 2 rindas bez `politician_id`.
- LIVS15 balsojumu nav; `parties.coalition_status` ir 14. Saeimas (SV-AJ = `not_in_saeima`) līdz vārtiem C (~2026-11-03).

## Lēmumi

| Jautājums | Lēmums | Kāpēc |
|---|---|---|
| Kura Saeima | **15.** Kods parametrizēts pēc sastāva faila, tāpēc 14. vai 16. ir viena datu faila maiņa. | 14. Saeimas lapa dzīvotu 4 nedēļas. |
| Kur dzīvo | Jauna `saeima.html`; augšējā izvēlnē «Tēmas» vietā (operators 2026-10-08), «Tēmas» pārceļas uz «Vairāk». Saite arī no `partijas.html` vēlēšanu bloka. | Abi nākotnes paplašinājumi (balsojuma pusloks, 14.→15. slīdnis) ir Saeimas, ne partiju tēma. |
| Sēdvietu kārtība | Pa sarakstiem no kreisās uz labo pēc vietu skaita dilstošā secībā — tā pati kārtība kā vēlēšanu blokā. Lapā rakstīts: «Kārtība — pēc saņemto vietu skaita, ne politiskā spektra.» | Neitrāla, pārbaudāma; nevajag mūsu viedokli par «kreiso» un «labo». |
| Ministri, kas nav deputāti | Nav v1. | Sastāvs = deputāti. |
| Statuss | Lapā redzama zīme «Provizoriski — CVK aprēķins, 04.10.» līdz oficiālajam sarakstam; tad faila aizstāšana. | Cieša cīņa (7–71 balss) — sastāvs vēl var mainīties. |

## Lēcas v1 (izvēlētas pēc tā, vai saucējs ir pilns)

| Lēca | Krāsa nozīmē | Saucējs | Avots |
|---|---|---|---|
| **Saraksts** (noklusējums) | ievēlētāja saraksts | 100/100 | sastāva fails + `parties.color` |
| **Balsoja 14. Saeimā** | jā / nē | 100/100 | `saeima_individual_votes` (precīzs vārds → `politician_id`). Nosaukums apzināti «balsoja», ne «atkārtoti ievēlēts»: ministrs, kurš 14. Saeimā nolika mandātu, balsojumos neparādās. |
| **Pozīcijas 90 dienās** | 0 / 1–4 / 5–19 / 20+ | tikai izsekotie (98 šodien) | `claims`, `claim_type='position'`, LV laiks |
| **Pretrunas** | publicēto pretrunu skaits (0 / 1 / 2+) | tikai izsekotie | `contradictions`, `confirmed=1` |

Neizsekots deputāts lēcās «Pozīcijas» un «Pretrunas» = pelēks raksts + teksts «nav datu», nekad zemākā krāsa. Katras lēcas leģendā: saucējs («dati par 98 no 100») un periods.

**Atliktas, ar atslēdzēju:**
- Koalīcija — kad 15. Saeima apstiprina valdību un `coalition_status` atjaunots (vārti C).
- Frakcijas disciplīna — kad ielādēti ≥30 LIVS15 balsojumi.
- Deklarācijas — kad VAD 2026 dati sasaistīti ar jaunajiem deputātiem.

## Arhitektūra

- **`src/render/saeima.py`** — `render_saeima(db, out_dir)`. Lasa sastāva failu ar `personas.py` jau esošo ielādētāju (pārnest uz `_common`, ja vajag kopīgu — nevis dublēt). Precīza vārda sakritība ar `tracked_politicians.name` (NEKĀDAS apakšvirknes — T1). Katrai sēdvietai aprēķina visas lēcu vērtības Python pusē.
- **SVG Python pusē:** matemātisks pusloks, 100 apļi rindās. Katrs aplis = `<a>` (fokusējams) ar `data-lens-*` atribūtiem un `aria-label` («Vārds Uzvārds, saraksts»). Bez JS lapa rāda Saraksta lēcu un strādā.
- **Saraksts zem puslokā:** grupēts pa sarakstiem, katrā rindā vārds + krāsas čips + teksta vērtība aktīvajai lēcai. Telefonā tas ir galvenais ceļš; pusloks ir pārskats.
- **Kartīte:** iepriekš renderēta slēpta `<div>` katram deputātam (nevis JSON) — vārds, saraksts, apgabals; izsekotajiem arī jaunākā pozīcija ar datumu un avota saiti, pretrunu skaits, «Pilnais profils →». Neizsekotajiem: «Profils vēl nav izveidots.»
- **`assets/slv1.js`** (`sav1.js` jau aizņemts saišu lapai) — lēcu pogas (pārslēdz klasi uz `<svg>`), kartītes atvēršana/aizvēršana, Esc, fokusa atgriešana. Bez inline JS (CSP).
- **Krāsas** — CSS tokeni gaišajam un tumšajam režīmam; lēcu skalas nav tikai krāsa: leģenda + teksta vērtība sarakstā un kartītē.
- **Renderēšana:** jauns domēns `--only=saeima`; `_orchestrator.py` reģistrācija.

## Kļūmes un vārti

- Sastāva fails nav vai nav 100 ierakstu → render KRĪT (nevis klusa tukša lapa).
- Saraksta numurs, kura nav `cvk_sv2026_rezultati.yaml` → KRĪT.
- Render izdrukā: `sēdvietas=100 izsekoti=N bez_profila=100−N`.

## Testi (CLAUDE.md 5. princips)

Viens e2e tests, rakstīts pirmais: renderē lapu no fixture DB + fixture sastāva faila un pārbauda (a) 100 sēdvietas, (b) izsekotajam ir profila saite, neizsekotajam nav, (c) neizsekotajam pozīciju lēcā ir «nav datu», nevis 0, (d) sastāva fails ar 99 ierakstiem → kļūda. CSP un inline-JS jau sedz `tests/test_no_inline_js.py` un `test_csp_external_hosts.py` — jaunu nepievienojam. `test_render_chars` bāzlīnija — REGEN tikai jaunajai lapai.

## Ārpus v1

Balsojuma pusloks, 14.→15. slīdnis, ministru rinda, deklarāciju lēca, sociālo tīklu attēls. Publicēšana — tikai ar operatora atļauju (Publish pause).
