# Claim-extractor prompta v4 — kodols + `support` vārti — 2026-09-30

Plāns un iepriekš fiksētie kritēriji: `docs/plans/2026-09-30-claim-extractor-parbuve.md`. Recepte, dati un palīgu uzdevumi: `docs/eval/stance-zelts-2026-09-30/` (`UZDEVUMS.md`, `build_gold.py`, `score.py`).

## Kas salīdzināts

- **vecais** — prompts `f4dd442b` (597 rindas; tajā jau ir v3 labojumi un 7. jautājums). Tātad eval mēra «jaunais ≥ pašreizējais», nevis «jaunais izlabo 16 %». Tie 16 % radās ar agrākām prompta versijām.
- **jaunais** — kodols (96 rindas) + 4 atsauces faili `.claude/references/claim-extractor/` + obligāts `support`.
- **Zelta kopa** — 38 doki no 09-30 verificētajām rindām: 26 ar B kļūdu (blakus fakts 5, jautājums 5, vilcinājums 5, laiks 3, cēlonis 3, tvērums 3, citu vārdi 2), 6 atsaukti (WITHDRAW), 6 D_OK kontrole. Izslēgti doki, kuru claim ID citē vecais prompts.
- **Skrējiens** — 5 komplekti pa 8 dokiem (kā produkcijā), abiem variantiem tie paši. DRY-RUN, DB netiek lasīta ne rakstīta. **Vērtēšana** — 3 akli vērtētāji pēc `RUBRIKA.md`, varianti sajaukti ar anonīmiem ID.

## Rezultāts

| | vecais | jaunais |
|---|---|---|
| Stance kopā | 24 | 30 |
| A+B (plašāks par avotu / nav pozīcija) | **0** | **0** |
| C (tikai valoda) | 0 | 0 |
| Atrastas pareizās pozīcijas (KEEP doki) | 24/32 | **28/32** |
| Viltus ekstrakcija uz WITHDRAW dokiem | 0/6 | 0/6 |
| `support` fragmenti avota tekstā | — | **30/30** |
| Garumzīmju kļūdas (`validate_lv_diacritics`) | 0 | 0 |
| 12 gadījumu suite (`prompt-golden-suite.md`) | 12/12 (09-22 v3) | 11/12 burtiski, 12/12 pēc būtības |

**Kritēriju pārbaude (fiksēti pirms skrējiena):**
1. A+B ≤ vecais − 5 pp — **nav pārbaudāms**: abi 0 %, no nulles nevar nokrist. Ne izpildīts, ne neizpildīts.
2. Atrasto skaits ≥ vecais − 1 — izpildīts (+4).
3. WITHDRAW ne vairāk kā vecajam — izpildīts (0 = 0).
4. `support` ≥ 95 % — izpildīts (100 %).
5. 0 garumzīmju kļūdu — izpildīts.
6. Suite 12/12 — 11/12 burtiski. 7. gadījumā (svinīgās sēdes runa) jaunais pozīciju izvilka pareizi, ar 0.6 un `NEEDS_REVIEW:`. Tieši to prasa CLAUDE.md eskalācija 2 (0.5–0.6 → marķieris). v3 skrējiens to pašu pozīciju glabāja ar 0.6 bez marķiera, tātad pārkāpa eskalāciju 2. Skripts `needs_review` skaita kā neatbilstību.

**Kur jaunais atrod vairāk:** doki 6387 (Liepnieks), 24062 (Kulbergs), 71133 (Treija — retorisks jautājums, stance «jautā, kura…»), 15393 (Kols), 4731 (Baško). Vecais tos atzīmēja tukšus vai uzrakstīja citu pozīciju. Vienā dokā vecais bija labāks: 13003 (Vītols) — jaunais izvilka tikai nosacījuma teikumu par Hormuzu, bez jautājuma par «Madman theory».

## Vērtētāja kalibrēšana — vai «0 kļūdu» ir īsts

Visi 54 stance D_OK. Tā var izskatīties arī vārti, kas nevar kristies. Tāpēc tas pats vērtētāja uzdevums tika palaists vēlreiz uz akla maisījuma: **32 zināmi kļūdaini stance** (tie, kas DB glabājās pirms 09-30 labojuma, verificēti A/B) + **10 eval stance**. Rezultāts:
- zināmi kļūdainie: **28/32 atzīmēti A/B** (23 B, 5 A);
- eval stance: 10/10 D_OK.

Vērtētājs kļūdas redz, tātad 0/54 ir mērījums, ne akls punkts. Orķestrators pats pārlasīja 6 dokus (13003, 71133, 28123, 26555, 28048, 26370) pret avotu un piekrīt.

## Ko šis mērījums NEPIERĀDA

- **n ir mazs**: 38 doki, viens skrējiens katram variantam. +4 atrastās pozīcijas ir virziens, ne statistiski drošs skaitlis.
- **Noplūdi no blakus dokiem un 12 doku dreifu tas neatveido**: komplektos bija dažādi politiķi un 8 doki, nevis viena politiķa pavediens. Pret šo klasi tagad mehāniski sargā `support` vārti (`src/support.py`): fragmentam jābūt ŠĪ dokumenta tekstā.
- **Slotu noteikumi** (žurnālisti, biroja balss, simulācija), kas pārcelti uz `sloti.md`, šajā kopā ir tikai 3 doki (visi žurnālistu relay; abi varianti tukši). Tos daļēji sedz 12 gadījumu suite (rituāls, RT, svinīga runa).
- **Kontaminācija**: jaunā melnrakstā bija piemērs «Madmans theory nostrādāja?» no zelta doka 13003. Pirms ieviešanas tas aizstāts ar neitrālu piemēru. Uz rezultātu tas neatstāja pozitīvu iespaidu: tieši šajā dokā jaunais bija vājāks.
- **Palīgi**: 10 ekstraktori + 1 suite + 3 vērtētāji. Vēl 3 vērtētāji tika palaisti atkārtoti, jo viens ekstraktors pārrakstīja savu failu pēc vērtēšanas ievades sagatavošanas; pirmā kārta apturēta. Plus 1 kalibrēšana. Kopā 18 Opus (plānā bija 14).
