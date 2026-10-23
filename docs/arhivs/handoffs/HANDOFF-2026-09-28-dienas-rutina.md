# Handoff 2026-09-28 (vakars) — dienas rutīna publicēta

**Stāvoklis:** rutīna 2026-09-28 pabeigta 11/11; pārskats #656 + attēls #350 live (deploy `13df46b6`, `verify_host` 9/9, varianti 4/4 → 200). Iepriekšējais handoff: `docs/HANDOFF-2026-09-28-nedelas-parskats.md`.

## Izdarīts
- Divi ingesti (942 doki), ekstrakcija 178/178 pāri, 43 pozīcijas, 0 pretrunu, spriedzes #400–#406, piezīmes #654, #655.
- «Pēdējā nedēļā» ziņu/pretrunu/balsojumu lapās = 7 dienas pēc LV laika (`dada1e14`).
- Datu labojumi — katram `data/fix*_2026-09-28.sql` + rollback pāris.

## Gaida operatoru
- Doc 118396 (LSM, klimats): Kulberga 2022. gada debašu citāts — ievadīt vēsturiski ar īsto datumu vai atstāt tukšu.
- `backlog/dati-db.md` § a8: «Līdaka» = zivs (3 Vēstneša doki), Zīle doc 118994 un Žuravļevs doc 119026 — nepareizas saites.
- Doc 119004 (jauns.lv viedoklis par aizsardzību): autors nav noteikts; ja tas ir izsekots politiķis, rakstā ir pozīcijas.
- Doc 118974 (LTV «X stunda Silgalē»): pid 151 Rasima un pid 204 NBS pāri vēl `extracted_at IS NULL`.
