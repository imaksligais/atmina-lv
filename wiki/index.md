# atmina — Indekss

_Atjaunots: 2026-10-31 22:54:26_

## Stāvoklis

- **228** politiķi, **10549** pozīcijas + **694604** Saeimas balsojumi, **46** pretrunas, **135239** dokumenti
- Saucējs: «politiķi» = tikai `relationship_type='tracked'` ieraksti; mediju, žurnālistu un iestāžu sloti nav ieskaitīti
- **35** tēmas, **33** likumi
- Pēdējais ingest: 2026-10-31 21:27
- Media pārklājums: mediāns 10 claims/politiķi, 33/228 bez neviena media claim
- Nepārskatīts backlog: 1 ziņu raksti
- Pārskatīti bez claims: 4556 (ceremoniāli/dublikāti — re-extraction var atgūt daļu)
- Lint: 0 orphans, 0 broken links, 0 stale frontmatter, 1 izolētas tēmas, 0 bojātas lapas
- Pēdējo 7 dienu media claims: Andris Kulbergs (34), Andris Velps (21), Jānis Dombrava (12), Aleksandrs Kiršteins (11), Ansis Pūpols (11)

## Struktūra

- [[persons/personas|Politiķi]] — 257 profili, 10498 pozīcijas (tikai aktīvie)
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
