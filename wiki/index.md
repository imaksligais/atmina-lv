# atmina — Indekss

_Atjaunots: 2026-10-10 23:18:50_

> **Kas mainījās 2026-04-11:** Pozīcijas un Saeimas balsojumi tagad tiek skaitīti atsevišķi. Agrāk "pozīciju" skaits apvienoja abus un izskatījās 8× lielāks par faktisko retorisko aktivitāti. Skaitļi nav mazāki — tie ir pārklasificēti.

## Stāvoklis

- **224** politiķi, **9243** pozīcijas + **680734** Saeimas balsojumi, **38** pretrunas, **118432** dokumenti
- Saucējs: «politiķi» = tikai `relationship_type='tracked'` ieraksti; mediju, žurnālistu un iestāžu sloti nav ieskaitīti
- **33** tēmas, **33** likumi
- Pēdējais ingest: 2026-10-10 22:57
- Media pārklājums: mediāns 9 claims/politiķi, 38/224 bez neviena media claim
- Nepārskatīts backlog: 1 ziņu raksti
- Pārskatīti bez claims: 4170 (ceremoniāli/dublikāti — re-extraction var atgūt daļu)
- Pēdējo 7 dienu media claims: Andris Kulbergs (90), Andris Šuvajevs (39), Edmunds Jurēvics (38), Ilze Indriksone (34), Edgars Tavars (34)

## Struktūra

- [[persons/personas|Politiķi]] — 253 profili, 9192 pozīcijas (tikai aktīvie)
- [[parties/partijas|Partijas]] — 18 partijas
- [[topics/temas|Tēmas]] — 33 tēmas
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
