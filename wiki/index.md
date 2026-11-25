# atmina — Indekss

_Atjaunots: 2026-11-24 23:49:56_

## Stāvoklis

- **239** politiķi, **12251** pozīcijas + **696294** Saeimas balsojumi, **54** pretrunas, **154630** dokumenti
- Saucējs: «politiķi» = tikai `relationship_type='tracked'` ieraksti; mediju, žurnālistu un iestāžu sloti nav ieskaitīti
- **35** tēmas, **33** likumi
- Pēdējais ingest: 2026-11-24 21:09
- Media pārklājums: mediāns 11 claims/politiķi, 27/239 bez neviena media claim
- Nepārskatīts backlog: 3 ziņu raksti
- Pārskatīti bez claims: 5193 (ceremoniāli/dublikāti — re-extraction var atgūt daļu)
- Pēdējo 7 dienu media claims: Andris Kulbergs (57), Matīss Žuravļevs (50), Kārlis Purgailis (36), Andris Velps (36), Ēriks Stendzenieks (35)

## Struktūra

- [[persons/personas|Politiķi]] — 269 profili, 12200 pozīcijas (tikai aktīvie)
- [[parties/partijas|Partijas]] — 18 partijas
- [[topics/temas|Tēmas]] — 35 tēmas
- [[mediji|Mediji]] — 11 mediju caurskatāmības profili (publiskā vietne `mediji.html`)
- [[laws/likumi|Likumi]] — 33 likumi
- `synthesis/` — 11 starppartiju analīzes
- [[operations/operacijas|Operācijas]] — rutīnas, rokasgrāmatas, aģentu apraksti
- [[operations/atmina-ops|atmina ops]] — lokāls operatora dashboard (`.venv/Scripts/python.exe serve.py`)
- [[log-ingest|Ielādes žurnāls]] — dokumentu ielādes vēsture

> **Saucēji.** «Stāvoklis» politiķi = `SELECT COUNT(*) FROM tracked_politicians WHERE relationship_type='tracked'` (īstie politiķi; mediju, žurnālistu un iestāžu sloti nav ieskaitīti). «Struktūra» profili = `SELECT COUNT(*) FROM tracked_politicians WHERE relationship_type!='inactive'` — tieši tik personu lapu `wiki_sync()` uzraksta, tāpēc šis skaitlis atbilst [[persons/personas]] virsrakstam. «Struktūra» pozīcijas = `SELECT COUNT(*) FROM claims c JOIN tracked_politicians tp ON tp.id=c.opponent_id WHERE c.claim_type='position' AND tp.relationship_type!='inactive'`; «Stāvoklis» pozīcijas skaita arī neaktīvo politiķu rindas, tāpēc ir lielākas.

## Paneļi (Bases)

- [[politiki.base|Politiķu dzīvais panelis]] — filtrē/kārto pēc partijas, pozīcijām, pretrunām
- [[pretrunas.base|Pretrunu fokuss]] — politiķi un partijas ar pretrunām

![[pretrunas.base#Politiķi ar pretrunām]]
