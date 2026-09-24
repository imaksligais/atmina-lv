Tu strādā repo `E:\atmina` (Latvijas politiķu izteikumu datubāze). Uzdevums ir norobežots, bet tajā ir slazds — izlasi visu pirms sāc.

## Problēma

`src/db.py` ap 372. rindu ir ceļš, kur **tas pats URL ar citu saturu pārraksta `documents.content`**. Saturs mainās, bet `document_politicians` junction rindas paliek tādas, kādas bija — arī tās, ko jaunais teksts vairs nepamato.

Audits (`scripts/audit_stale_politician_links.py`) šodien atrada **35 tādas rindas** — klase `teksts_nomainits`.

## Slazds, kura dēļ naivs labojums ir BĪSTAMS

Acīmredzamais labojums — «pārrakstot saturu, pārlaid saistītāju un izdzēs rindas, ko jaunais teksts nepamato» — **var dzēst patiesas piesaistes**.

Iemesls ir pierādīts tajā pašā auditā: mūsu glabātais teksts bieži ir **nogriezta ekstrakcija**, ne pilns raksts. Klase `varda_nav_tekstā` = 51 rinda, un doc 42838 ir pierādījums — glabāti 313 vārdi ar vienu nosauktu politiķi, kamēr dzīvajā NRA rakstā 16 ministri tiešām ir (pārbaudīts ar `curl` 2026-09-22). Ja pārrakstīšana atnes īsāku vai nogrieztu tekstu, naivs labojums nodzēsīs 16 pareizas piesaistes.

Tāpēc: **dzēšana drīkst notikt tikai tad, kad ir pierādījums, ka jaunais teksts ir pilnvērtīgs, nevis īsāks/nogriezts.**

## Ko izdarīt

1. Izpēti `src/db.py` `save_document` (ap 352.–425. r.) un noskaidro precīzi, kad notiek satura pārrakstīšana.
2. Piedāvā un ievies **konservatīvu** noteikumu. Piemēram (tev jāizvēlas un jāpamato): pārlaist saistītāju un noņemt nepamatotās rindas tikai tad, ja jaunais teksts ir **garāks** par veco un neizskatās nogriezts; pretējā gadījumā saturu pārrakstīt, bet junction **neaiztikt**.
3. Ja secini, ka droša automātiska dzēšana nav iespējama, **tā arī saki** un ievies vājāko variantu: atzīmē dokumentu pārskatīšanai (piem., ieraksts `review_status` vai atsevišķs log), nevis dzēs.
4. Testi `tests/` — gan uz to, ka nepamatotā rinda tiek noņemta pareizajā gadījumā, gan **it īpaši** uz to, ka nogrieztā/īsākā gadījumā tā NETIEK noņemta.

## Aizliegts

- **Nekādu dzēšanu dzīvajā DB.** Kods drīkst dzēst tikai testos pret pagaidu/in-memory DB. Nekādu vienreizēju «iztīrīšanas» skriptu palaišanu pār `data/atmina.db`.
- Dzīvo DB atver tikai `mode=ro`, ja vispār vajag.
- Nekādu `git commit`, `git push`, deploy vai renderēšanu.
- Nemaini nesaistītus failus.

## Vārti, kas jāpalaiž pašam

```
cd /e/atmina
env -u PYTHONPATH .venv/Scripts/python.exe -m pytest tests/ -q -x
env -u PYTHONPATH .venv/Scripts/python.exe scripts/audit_stale_politician_links.py --limit 400
```

Pilnā suita ir ~2800 testi un aizņem ~5 min — palaid to, ne tikai vienu failu.

## Atskaite

Ko mainīji, kāds ir izvēlētais noteikums un **kāpēc tas nevar nodzēst patiesu piesaisti**, kādi testi to pierāda, pytest izvade. Ja izvēlies nedarīt automātisku dzēšanu — paskaidro, kas tieši tevi pārliecināja. **Negatīvs rezultāts ar pierādījumu ir derīgs rezultāts**; nespied izmaiņu cauri, lai uzdevums izskatītos izpildīts.
