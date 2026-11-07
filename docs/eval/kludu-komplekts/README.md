# Claim-extractor kļūdu komplekts v2 — recepte

Kļūdu komplekts ir neliels, iesaldēts dokumentu kopums. **Pagaidu** precizitātes screen: to var palaist pirms `claim-extractor` prompta maiņas, bet bāzes skrējienā 2026-10-14 tas nespēja atšķirt bojātu promptu (sk. sadaļu beigās), tāpēc tas vēl nav obligāti vārti. Pašlaik 37 gadījumi. Tas atbild uz vienu jautājumu: vai jaunais prompts nav sliktāks par pašreizējo tajās kļūdu klasēs, ko auditi jau ir atraduši.

Plāns un pamatojums: `docs/plans/archive/2026-10-14-kludu-komplekts-v2.md`. Iepriekšējā versija (v1, piesātināta): `docs/eval/stance-zelts-2026-09-30/`.

## Kas ir komplektā

- Gadījums ir **viss dokuments** vienam politiķim, ne viens claim.
- Katram gadījumam ir:
  - `expected` — `KEEP` (dokumentā ir pozīcija) vai `EMPTY` (pozīcijas nav);
  - `must` — pozīcijas, kas jāatrod, ar pieļaujamām alternatīvām;
  - `forbidden` — konkrēta pārsniegšana, ko audits atrada (piemēram, noņemta atruna vai partijas programma, kas uzdota par paša pozīciju);
  - `tags` — kļūdu klases; viens gadījums var būt vairākās.
- Klases: citu cilvēku vārdi, partijas teksts, noņemti nosacījumi, apmelojuma atrunas, paplašināts tvērums, fakti ārpus dokumenta, jautājums/laiks/cēlonis, «nav pozīcijas», pozitīvie gadījumi, garas stenogrammas un tīras kontroles.
- Dokumentu tekstus un atbildes šeit nepublicē. Iemesls: tie identificē gadījumus un var nonākt nākamajā promptā (kontaminācija).

## Kur ir faili

Visi iesaldētie faili ir mapē `docs/audits/kludu-komplekts-v2/`. Šī mape **nav publiskajā spogulī** (`docs/funding/repo-sync.md`).

| Fails | Saturs |
|---|---|
| `cases.json` | gadījumi ar atbildēm, `doc_text`, `doc_sha256` un paketes numuru |
| `packs/pNN.json` | ekstraktora ievade bez atbildēm, pa 8 dokiem; katra stenogramma savā paketē |
| `MANIFEST.json` | sha256 katram iesaldētajam failam |
| `freeze.py` | iesaldē gadījumus no DB (tikai lasot) |
| `contamination.py` | pārbauda, vai komplekts nav noplūdis promptā |
| `score.py` | vērtēšanas ievade, atskaite un lēmums |
| `runs/<datums-nosaukums>/` | katrs skrējiens savā mapē: `prompt-<variants>/`, `out/`, `grade_in/`, `grade_out/`, `report_<pašreizējais>_<jaunais>.json` |

Skrējiena izvade pēc `prep` nav maināma. `score.py` glabā `out/` failu sha256 un apstājas, ja kāds fails ir mainījies. Labojums = jauns skrējiens jaunā mapē.

## Varianti

Variants ir **prompta fails un atsauces faili, uz kuriem tas norāda**.

- `HEAD` — pašreizējais `.claude/agents/claim-extractor.md` ar `.claude/references/claim-extractor/`.
- `HEAD-2` — tas pats `HEAD` otrreiz. Tas mēra troksni: cik gadījumu krīt nejauši.
- `mutant` — `HEAD` kopija bez trim noteikumiem, kas sedz komplekta klases. Ja komplekts mutantu neizķer, tas šīs klases nesedz.
- `jaunais` — kandidāta prompts, kad komplektu lieto kā vārtus.

Ja variants maina arī atsauces failus, tos kopē uz `RUN/prompt-<variants>/` un promptā nomaina ceļus uz kopijām. Citādi variants joprojām lasa `HEAD` atsauces, un mutants nav mutants.

Varianta nosaukumā nedrīkst būt `_`.

## Soļi

Visas komandas palaiž no repo saknes ar `PYTHONUTF8=1` un `.venv/Scripts/python.exe`. Zemāk `PY` = `.venv/Scripts/python.exe`, `KK` = `docs/audits/kludu-komplekts-v2`, `RUN` = `$KK/runs/<datums-nosaukums>`.

1. **Operatora «jā» ar skaitu.** Palīgu skaits = varianti × paketes ekstraktori + 4 vērtētāji (3 akli + 1 recall).
2. **Iesaldēšana** (vienreiz; atkārtojumam jādod tās pašas paketes):
   `PY $KK/freeze.py $KK/cases_draft.json`
   Atkārtota palaišana uz `$KK/cases.json` pārbauda, ka paketes sakrīt un ka DB dokumenti nav mainījušies (`doc_sha256`). Atbilžu labojumi (`must`, `forbidden`, `notes`) paketes nemaina un ir atļauti. Ja paketes mainītos (piemēram, DB mainījies `feed_type` vai loma), skripts apstājas. Apzinātai pārbūvei: `--refreeze`.
3. **Kontaminācija** — katrā skrējienā, arī kandidāta promptam:
   `PY $KK/contamination.py [RUN/prompt-jaunais/claim-extractor.md ...]`
   Skripts pārbauda arī failus, uz kuriem prompti norāda (`.claude/references/`, prompta mape, `RUBRIKA.md`), un izdrukā visus pārbaudītos failus. Krīt, ja promptā ir gadījuma doc vai claim ID vai ≥40 zīmju gabals no gadījuma teksta. Skripts izdrukā, cik gadījumu un failu pārbaudīja.
4. **Ekstraktori** — viens palīgs katram (variants, pakete); uzdevums zemāk.
5. **Aklā ievade:** `PY $KK/score.py prep RUN HEAD HEAD-2 mutant`
   Apstājas, ja kāds doks trūkst, atkārtojas vai ir liekā paketē.
6. **3 akli vērtētāji** — katrs vērtē VISUS stance no `RUN/grade_in/all.json`, raksta `RUN/grade_out/r1.json`, `r2.json`, `r3.json`.
7. **Recall ievade:** `PY $KK/score.py prep2 RUN`, tad 1 recall vērtētājs → `RUN/grade_out/recall.json`.
8. **Atskaite:** `PY $KK/score.py report RUN HEAD jaunais` (bāzes skrējienā: `HEAD mutant` un `HEAD HEAD-2`).
9. **Apstiprināšana**, ja atskaite saka «AIZDOMAS»: skartās paketes abiem variantiem palaiž vēl 2× jaunās mapēs `RUN2`, `RUN3`:
   `PY $KK/score.py prep RUN2 HEAD jaunais --packs p01,p03`, soļi 6–8, tad
   `PY $KK/score.py confirm HEAD jaunais RUN RUN2 RUN3`
10. **Pārējie vārti:** 12 gadījumu suite (`docs/eval/prompt-golden-suite.md`) 12/12.
11. **Kopsavilkums** šajā mapē, bez dokumentu tekstiem un ID.

## Lēmuma noteikums

Noteikums mainīts 2026-10-14 pēc bāzes skrējiena. Gadījuma vērtējumam ir divas daļas.

**Precizitāte** — gadījums **krīt**, ja:
- vismaz 2 no 3 vērtētājiem kādam tā stance dod A vai B;
- ir kāds `forbidden`;
- `EMPTY` dokā ir ekstrahēts kaut viens claim.

**Pārklājums** — cik `must` atrasts. To parāda katram variantam un tagam, bet gadījums no tā nekrīt.

**Screen** skatās tikai precizitāti. Precizitātes regresija ir gadījums, kur jaunais krīt, bet pašreizējais iztur. «AIZDOMAS», ja:
- jaunajam ir vismaz 2 precizitātes regresijas;
- VAI kaut viena precizitātes regresija ir `EMPTY` vai `allegation` gadījumā;
- VAI jaunais neiziet cietos vārtus (zemāk).

Izlabojumi citos gadījumos regresijas neatsver: skaita regresijas, ne starpību. Citādi «IZTUR».

**Apstiprināšana.** Aizdomu gadījumā skartās paketes abiem variantiem palaiž vēl 2× ar to pašu modeli. «BLOĶĒ», ja jaunā precizitātes defekts atkārtojas vismaz 2 no 3 reizēm un pašreizējais iztur vismaz 2 no 3. Neizšķirts ir «NAV PIERĀDĪTS», nevis «iziet».

**Cietie vārti jaunajam:** `support` ≥ 95 % un 0 garumzīmju kļūdu tā stance. Ja kāds no tiem neiziet, atskaite saka «AIZDOMAS» arī tad, ja gadījumi iztur. Pašreizējā varianta vārtu rezultātu tikai parāda. Apstiprināšanā vārti bloķē, ja jaunais tos neiziet vismaz 2 no 3 skrējieniem. Suite 12/12 pārbauda atsevišķi. Uzlabojumi citos gadījumos nekompensē jaunu `attribution` vai `allegation` defektu.

**Manifests.** `prep` ieraksta `RUN/MANIFEST.json` sha256 visiem lēmuma ievades failiem: iesaldētajām paketēm, `cases.json`, `RUN/prompt-*/`, `out/`, `grade_in/`, `_sid_map.json`. `prep2` pievieno `_rid_map.json`. Pirmais veiksmīgais `report` aizzīmogo `grade_out/`. Ja kāds no šiem failiem pēc tam mainās vai parādās jauns, `report` un `confirm` apstājas. `confirm` katru skrējienu pārrēķina no ievades failiem, ne no `report_*.json`.

## Bāzes skrējiens 2026-10-14

- Varianti: `HEAD`, `HEAD-2` un `mutant`. Abi salīdzinājumi (`HEAD`↔`HEAD-2` un `HEAD`↔`mutant`) deva «IZTUR» gan pēc vecā, gan pēc jaunā noteikuma.
- Troksnis: starp diviem vienādiem skrējieniem pēc vecā noteikuma 4 gadījumi mainīja rezultātu (2 regresijas un 2 izlabojumi). Tikai pēc precizitātes — 3 (1 regresija un 2 izlabojumi).
- Mutantu komplekts neizķēra. Tātad jutība pret regresijām **nav pierādīta**.
- Pagaidām komplekts ir provizorisks precizitātes screen un dokumentētu regresiju piemēru krājums, ne vārti, kas pierāda, ka prompts nav sliktāks.
- Vērtētāji palaida garām vienu mutanta gadījumu, kur bija nomesta apmelojuma atruna.

## Ekstraktora uzdevums ({VARIANT}, {PACK})

```text
Tu esi @claim-extractor eval skrējienā (DRY-RUN). Darba mape E:\atmina.

1. Tavi noteikumi ir failā {PROMPT} — izlasi to pilnībā un ievēro kā savu aģenta promptu. Drīksti lasīt failus, uz kuriem noteikumi norāda (atsauces failus, rubriku, src/topic_map.py).
2. Ievade: E:\atmina\docs\audits\kludu-komplekts-v2\packs\{PACK}.json — dokumenti, katram norādīts politiķis (pid, vārds, slota tips), kura pozīcijas meklēt. Tas ir tas, ko tev būtu devis get_politician_documents().
3. DRY-RUN: DB neizmanto vispār — nekādu src.* importu, sqlite, save_analysis, get_*, search_similar_claims, store_*. Dublikātu un pretrunu soļus izlaid (nav pieejami).
4. Nelasi NEKO citu mapēs docs/audits un docs/eval, izņemot {PROMPT} un failus, uz kuriem tas norāda, savu paketes failu un RUBRIKA.md. Tur ir atbildes.
5. Katram dokumentam pieņem lēmumu tieši tā, kā to darītu īstā rutīnā, un pieraksti claim dict tieši tādus, kādus nodotu save_analysis (ar tiem laukiem, ko prasa TAVI noteikumi).
6. Raksti TIKAI failu {RUN}\out\{VARIANT}_{PACK}.json: JSON masīvs, viens objekts katram dokumentam ievades secībā:
   {"doc_id": N, "pid": N, "decision": "extract"|"empty", "empty_reason": "…"|null, "claims": [ {claim dict}, … ]}
   Kad fails ir uzrakstīts, to vairs nemaini.
7. Aizliegts: git komandas, kas maina stāvokli (stash, checkout --, restore, reset, commit, add); jebkuru citu failu rakstīšana. Ja vajag Python: E:\atmina\.venv\Scripts\python.exe ar PYTHONUTF8=1.
Atbildē tikai viena rinda: cik dokumentu apstrādāts, cik claims, cik empty.
```

## Aklā vērtētāja uzdevums ({N} = 1, 2, 3)

```text
Tu esi akls stance vērtētājs. Darba mape E:\atmina.

1. Izlasi E:\atmina\docs\audits\2026-09-30-stance-izlase\RUBRIKA.md — tā ir tava rubrika.
2. Ievade: {RUN}\grade_in\all.json — dokumenti; katram doc_text, politiķis un saraksts ar stance (anonīmi id "sNNN", jaukta secība, dažādu autoru).
3. Novērtē VISUS stance. Katram: grade (A_WITHDRAW|B_REWRITE|C_LANGUAGE|D_OK|U_UNVERIFIABLE) pēc rubrikas, vērtējot TIKAI pret doc_text. Īss why (angliski, 1 teikums).
4. Vērtē katru stance neatkarīgi; nemeklē, kurš to uzrakstīja.
5. Raksti TIKAI {RUN}\grade_out\r{N}.json: JSON masīvs [{"sid": "sNNN", "grade": "…", "why": "…"}].
6. Tikai lasīšana; nekādas DB rakstīšanas; nekādu git mutāciju; neraksti citus failus. Mapē docs/audits/kludu-komplekts-v2 nelasi neko, izņemot savu ievades failu (ne out/, ne cases.json, ne _sid_map.json, ne citu vērtētāju failus).
Atbildē tikai viena rinda: cik stance novērtēts un sadalījums pa pakāpēm.
```

## Recall vērtētāja uzdevums

```text
Tu esi recall vērtētājs. Darba mape E:\atmina.

1. Ievade: {RUN}\grade_in\recall.json — vienības "rNNN"; katrā doc_text, viena anonīma autora stance saraksts, "must" (pozīcijas, kas jāatrod; proposition + alternatives + support fragmenti no dokumenta) un "forbidden" (pārsniegšanas, kuru nedrīkst būt).
2. Katram must: "found", ja tā pamatapgalvojumu un visus nosacījumus, kas maina nozīmi (atrunas, «ja», «varētu», tvērumu), pauž kāds stance vai vairāki stance kopā — pārklājums drīkst būt sadalīts pa vairākiem claims. Vārdiem nav jāsakrīt. Detaļas, kas "alternatives" laukā norādītas kā neobligātas, nav vajadzīgas. Ja trūkst pamatapgalvojuma vai nozīmi mainoša nosacījuma, tas ir "not_found". NEEDS_REVIEW marķieris claim pamatojumā pats par sevi nav kļūda — tādu claim skaiti kā parastu.
3. Katram forbidden: "present", ja kāds stance satur šo pārsniegšanu; citādi "absent".
4. Vērtē katru vienību atsevišķi; nemeklē, kurš to uzrakstīja.
5. Raksti TIKAI {RUN}\grade_out\recall.json: JSON masīvs
   [{"rid": "rNNN", "must": [{"mid": "m1", "verdict": "found"|"not_found", "why": "…"}], "forbidden": [{"fid": "f1", "verdict": "present"|"absent", "why": "…"}]}]
6. Tikai lasīšana; nekādas DB rakstīšanas; nekādu git mutāciju; neraksti citus failus. Mapē docs/audits/kludu-komplekts-v2 nelasi neko, izņemot savu ievades failu.
Atbildē tikai viena rinda: cik must atrasts / nav atrasts, cik forbidden ir.
```

## Divas piezīmes
- Vērtējumi ir aizzīmogoti tikai pēc pirmā `report`. Palaid `report` uzreiz, kad vērtētāji pabeiguši.
- Īstai prompta maiņai vajag 2 × 7 ekstraktorus + 3 aklus vērtētājus + 1 recall vērtētāju + 1 (12 gadījumu suite) = 19 Opus.
