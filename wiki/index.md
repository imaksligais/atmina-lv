# atmina — Indekss

_Atjaunots: 2026-08-22 08:19:34_

> **Kas mainījās 2026-04-11:** Pozīcijas un Saeimas balsojumi tagad tiek skaitīti atsevišķi. Agrāk "pozīciju" skaits apvienoja abus un izskatījās 8× lielāks par faktisko retorisko aktivitāti. Skaitļi nav mazāki — tie ir pārklasificēti.

## Stāvoklis

- **167** politiķi, **6030** pozīcijas + **650890** Saeimas balsojumi, **29** pretrunas, **79637** dokumenti
- Saucējs: «politiķi» = tikai `relationship_type='tracked'` ieraksti; mediju, žurnālistu un iestāžu sloti nav ieskaitīti
- **62** tēmas, **33** likumi
- Pēdējais ingest: 2026-08-21 22:35
- Media pārklājums: mediāns 6 claims/politiķi, 22/167 bez neviena media claim
- Nepārskatīts backlog: 222 ziņu raksti
- Pārskatīti bez claims: 2898 (ceremoniāli/dublikāti — re-extraction var atgūt daļu)
- Lint: 0 orphans, 0 broken links, 0 stale frontmatter, 23 izolētas tēmas, 0 bojātas lapas
- Pēdējo 7 dienu media claims: Andris Kulbergs (41), Edgars Rinkēvičs (14), Viktors Valainis (13), Atis Švinka (12), Jānis Dombrava (12)

## Struktūra

- [[persons/personas|Politiķi]] — 167 profili, 5978 pozīcijas (tikai aktīvie)
- [[parties/partijas|Partijas]] — 18 partijas
- [[topics/temas|Tēmas]] — 62 tēmas
- [[mediji|Mediji]] — 11 mediju caurskatāmības profili (publiskā vietne `mediji.html`)
- [[laws/likumi|Likumi]] — 33 likumi
- `synthesis/` — 9 starppartiju analīzes
- [[operations/operacijas|Operācijas]] — rutīnas, rokasgrāmatas, aģentu apraksti
- [[operations/atmina-ops|atmina ops]] — lokāls operatora dashboard (`.venv/Scripts/python.exe serve.py`)
- [[log-ingest|Ielādes žurnāls]] — dokumentu ielādes vēsture

## Paneļi (Bases)

- [[politiki.base|Politiķu dzīvais panelis]] — filtrē/kārto pēc partijas, pozīcijām, pretrunām
- [[pretrunas.base|Pretrunu fokuss]] — politiķi un partijas ar pretrunām

![[pretrunas.base#Politiķi ar pretrunām]]
