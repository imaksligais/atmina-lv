# atmina — Indekss

_Atjaunots: 2026-07-24 00:01:13_

> **Kas mainījās 2026-04-11:** Pozīcijas un Saeimas balsojumi tagad tiek skaitīti atsevišķi. Agrāk "pozīciju" skaits apvienoja abus un izskatījās 8× lielāks par faktisko retorisko aktivitāti. Skaitļi nav mazāki — tie ir pārklasificēti.

## Stāvoklis

- **189** politiķi, **4775** pozīcijas + **541763** Saeimas balsojumi, **29** pretrunas, **60320** dokumenti
- **32** tēmas, **33** likumi
- Pēdējais ingest: 2026-07-23 23:11
- Media pārklājums: mediāns 5 claims/politiķi, 36/189 bez neviena media claim
- Nepārskatīts backlog: 548 ziņu raksti
- Pārskatīti bez claims: 3838 (ceremoniāli/dublikāti — re-extraction var atgūt daļu)
- Lint: 1 orphans, 0 broken links
- Pēdējo 7 dienu media claims: Andris Kulbergs (32), Ainārs Šlesers (24), Māris Kučinskis (20), Andrejs Elksniņš (18), Ansis Pūpols (18)

## Struktūra

- [[persons/personas|Politiķi]] — 189 profili, 4723 pozīcijas
- [[parties/partijas|Partijas]] — 18 partijas
- [[topics/temas|Tēmas]] — 32 tēmas
- [[mediji|Mediji]] — 11 mediju caurskatāmības profili (publiskā vietne `mediji.html`)
- [[laws/likumi|Likumi]] — 33 likumi
- `synthesis/` — 8 starppartiju analīzes
- [[operations/operacijas|Operācijas]] — rutīnas, rokasgrāmatas, aģentu apraksti
- [[operations/atmina-ops|atmina ops]] — lokāls operatora dashboard (`python serve.py`)
- [[log-ingest|Ielādes žurnāls]] — dokumentu ielādes vēsture

## Paneļi (Bases)

- [[politiki.base|Politiķu dzīvais panelis]] — filtrē/kārto pēc partijas, pozīcijām, pretrunām
- [[pretrunas.base|Pretrunu fokuss]] — politiķi un partijas ar pretrunām

![[pretrunas.base#Politiķi ar pretrunām]]
