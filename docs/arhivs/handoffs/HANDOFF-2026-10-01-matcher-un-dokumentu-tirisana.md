# Handoff 2026-10-01 — matcher C + junction pārrēķins; nākamais: dokumentu tīrīšana

> **Statuss:** dokumentu tīrīšana IZPILDĪTA 2026-10-01 (`c99e0041`, `079da816`; CHANGELOG 2026-10-01 (4)). Paliek § Atvērts operatoram + CLAUDE.md sadaļu pārbūves lēmums (CHANGELOG ieraksta pēdējā rinda).

## Izdarīts (pēda: CHANGELOG 2026-10-01 (1)–(3), `git log --since=2026-10-01`)
- Matcher: LIELO burtu uzvārdi, vesels @handle, handle ≠ «tikai kopīgs uzvārds»; Vēstneša ingest filtrs; projekta konta filtrs visām platformām.
- Junction vēsture: +117 (caps/handle) un +6 580 (pilns pārskenējums, tikai pieminējumi); rollback faili `data/rollback_{caps_handle_junctions,rescan_mentions}_2026-10-01.sql`.
- Testi: `get_db` piesaistes noplūde salabota + `tests/conftest.py` § 5 vārti. check.sh 3280 passed.
- Nav deployots: jaunās saites lapās parādīsies ar nākamo render + deploy.

## Nākamais uzdevums (operators 10-01): dokumentu tīrīšana
Mērķis — optimāls garums, bez lieka. Sākuma izmēri: `CLAUDE.md` 46 153 B; `BACKLOG.md` + `backlog/*.md` 207 870 B (`wc -c`).
- Mēri pirms un pēc (`wc -l -c`), sadalījumu pa sadaļām — kā BACKLOG.md preambulas 2026-08-27 mērījums.
- Backlog: izgriež pabeigto TIKAI, ja pēda ir commit ziņā vai CHANGELOG (pārbaudi ar grep); § Ne-darīt ir apzināts izņēmums.
- `CLAUDE.md` sinhronizējas uz publisko spoguli; sadaļu numurus (Data Contract #N, inv #N, T#) nemaina — uz tiem atsaucas testi un prompti.
- Lielāka pārbūve = plāns pirms diff (globālais noteikums 8).

## Atvērts operatoram
- `backlog/matcher.md` § LIELO burtu un handle labojumu atlikumi (a)–(d).
- 384 atturētās `subject` rindas — § «`subject`» lomai vajag runātāja pierādījumu.

## Papildināts 2026-10-01 vakarā — verdiktu kārta izpildīta

- **Verdikti 2026-10-01** (22 rindas) izpildīti `8f86632c` + šis: per-rinda statuss un **9 atvērtie operatora jautājumi** — `docs/verdikti-2026-10-01.md` § Atvērtie jautājumi. CHANGELOG 2026-10-01 (6).
- **Divi mērījumi apgāza ieteikumus:** `subject` tikai ar runātāju — recall 84 % / 94 % (< 97 % vārti), NEieviests; foto-sepia noklusējums — 19/20 apstiprinātie hero ir sepia, tāpēc tikai izvēle.
- **Atrasts un labots:** Vēstneša filtrs nogrieza parakstītājus un 30 politiķu pilno vārdu (tests + mutācija; dzīvā ielāde vēl nav bijusi — pirmajā Vēstneša ielādē pārbaudi saišu skaitu).
- **NAV deployots:** visas šodienas DB izmaiņas (junction +6 580 + 384, citāti/stance, 396/Lp14) parādīsies tikai pēc render ar `politiki` + deploy ar operatora «jā».
- **Publiskais spogulis:** `c7e6eda` satur stāvokli līdz `59d81eca`; šīvakara commiti (`8f86632c`→) tajā vēl NAV — atsevišķs operatora solis.
- **Apstiprināts izpildei nākamajā sesijā (operators 2026-10-01 vakarā):** `docs/verdikti-2026-10-01.md` § Atvērtie jautājumi 1–5 un 9 (6 slēgts, 7 paliek `relay`, 8 atvērts). Darbs mazs — viens labojumu skripts + rollback, bez palīgu fan-out.
- **Nākamās sesijas secība (ieteikums):** vakara rutīna → render + deploy → `later` tvītu pārbaudes kārta (65 ievades faili, ~60–90 Opus palīgi — vajag «jā» ar skaitu).
- **Izpildīts 2026-10-01 (vēlāk):** atvērtie jautājumi 1–5 un 9 — CHANGELOG 2026-10-01 (7); atvērts paliek tikai 8 (Zalāns). Deployots 2026-10-01 (pilns renders, versija `f5fb5177`, verify_host 9/9). **Nākamā sesija = tikai rutīna.** Publiskais spogulis joprojām `c7e6eda` (atsevišķs operatora solis).
