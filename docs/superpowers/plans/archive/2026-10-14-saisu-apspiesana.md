# Plāns: apzināti noņemtas politiķa↔dokumenta saites vairs neatgriežas (D2 pilnais risinājums)

2026-10-14. Melnrakstu pārskatīja advisor un GPT-6-Astra; abu labojumi iestrādāti zemāk, nesaskaņas atzīmētas. Izpēte: `docs/audits/2026-10-14-datu-kvalitate/D2-saites-atgriezas.md`. 0. solis izpildīts (`19b5cd92`): pārielāde nepieliek otru lomu jau piesaistītam politiķim. **Ieviešana tikai pēc operatora «jā».**

## Mērķis
Saite vai loma, ko cilvēks apzināti noņēmis, neatgriežas ne caur ingest, ne matcher, ne rescan, un katrs atteikums ir redzams. Vecie rollback faili (87 skar junction: 25 tikai DELETE, 34 tikai INSERT, 28 jaukti) turpina strādāt bez izmaiņām.

## Fakti
- Rakstītāji: `src/db.py` (`_merge_links_keep_doc`, same-URL update, jauns doks, `link_politician_to_document` — manuāls), `src/matcher.py:1279`, `src/social.py:79`, `src/video_ingest/db.py:51`; skripti `backfill_x_junctions.py`, `audit_junction_roles.py`.
- `src/` nekad nedzēš un nemaina `role`; to dara tikai labojumu skripti un `data/*.sql` → dzēšana/lomas maiņa = cilvēka lēmums.
- `get_db()`: `foreign_keys=ON`, `recursive_triggers` nav iestatīts. Testi un produkcija iegūst shēmu vienā ceļā: `init_db()` → `schema.sql` + `db_migrations.apply_migrations` (precedents: `claims_review_status` trigeri). Izņēmums: `tests/test_video_ingest_finalize.py` atmiņas shēma — jāpapildina.

## Dizains
1. **Tabula** `document_politician_suppressions(document_id → documents ON DELETE CASCADE, politician_id, role, scope ∈ {'role','pair'}, reason, created_at UTC, lifted_at UTC NULL)`; PK `(document_id, politician_id, role)`. Rinda netiek dzēsta — atcelšana = `lifted_at` (pierādījums paliek auditam).
2. **Ierakstīšana ar trigeriem** (labojumam nekas nav jāatceras):
   - `AFTER DELETE`: ja pārim vairs nav nevienas rindas → `scope='pair'`, citādi `scope='role'`; `role=OLD.role`; `reason='auto-delete'`. Kaskādē no `documents` dzēšanas nav vajadzīgs sargs (FK kaskāde iztīra arī apspiešanu).
   - `AFTER UPDATE OF role WHEN OLD.role IS NOT NEW.role`: apspiež OLD (`scope='role'`, `auto-demote`), atceļ NEW.
   - `AFTER INSERT` (tikai tieša, ne caur palīgu — palīgs apspiestu neievieto): atceļ rindu ar `role=NEW.role`; tā paša pāra `scope='pair'` rindas pārvērš par `scope='role'` (tipisks labojums «DELETE subject → INSERT mentioned» atstāj apspiestu tikai `subject`). Ignorēts dublikāts (`INSERT OR IGNORE` uz esošu rindu) trigeri nepalaiž — pārbaudīts tests.
   - Labojuma SQL drīkst pēc tam `UPDATE … SET reason='<faila vārds>'`.
3. **Viens rakstītājs** `src.db.link_document_politicians(db, doc_id, links, *, source)`: vienā transakcijā izlaiž `(pid, r)`, ja ir neatcelta rinda ar `role=r` vai `scope='pair'`; piemēro 0. soļa noteikumu; katru izlaisto ieraksta `logs` (`dp_suppressed`, kā `suspect_link_flag`) un atgriež skaitu. Matcher kopsavilkums rāda «apspiesti N»; `insert_document` atgriešanas tips nemainās (skaits logā). Visi `src/` rakstītāji + 2 skripti pāriet uz palīgu. `link_politician_to_document` paliek manuāls (trigeris atceļ, stderr brīdinājums).
4. **Strukturāls tests**: `INSERT … INTO document_politicians` atļauts tikai palīgā un uzskaitītos failos (nosaukti saraksts, ne `fix_*` maska).

## Atvērts operatora lēmums (advisor 1. punkts)
Rollback, kas atsauc **kļūdainu pievienošanu** (piem., `/seed-entity` rescan ar par plašu vārda formu → rollback dzēš 50 saites), ierakstītu 50 apspiešanas, un pēc vārda formas labošanas pareizās saites vairs neatgrieztos.
- **Ieteikts (a):** vienas rindas slēdzis `dp_suppression_mode` (`record`/`off`); rollback-ģenerators pievienošanas atsaukumiem raksta `off` … DELETE … `record`. Ja kāds aizmirst — rodas **pārliekas** apspiešanas (droša puse: «stop beats write»), redzamas audita (c) sarakstā.
- (b) apspiešana tikai pēc labojuma skaidras atzīmes — aizmiršana = kluss atgriezums (šodienas kļūda). Nav ieteikts.

## Soļi (katrs = commits; DB mutācija tikai ar rollback, commitotu pirms)
1. **Testi vispirms** (krīt uz pašreizējā koda): galvenais E2E — dokam reāli izdzēš vienīgo saiti ar SQL; pēc tam same-URL ingest ar mainītu tekstu UN `link_politicians_to_documents(doc_ids=…)`, arī ar citu ierosināto lomu → saite neatgriežas, `dp_suppressed` logs ir, nesaistīta jauna saite tiek pievienota, un vecā stila rollback INSERT saiti atjauno. Atsevišķi trigeru gadījumi: UPDATE role turp un atpakaļ, `SET role=role`, `UPDATE OR IGNORE`, DELETE→INSERT demote, dokumenta kaskāde. Mutācija: noņem filtru palīgā → krīt.
2. **Migrācija + palīgs + visi rakstītāji vienā commitā** (lai nav starpstāvokļa, kur trigeri raksta, bet neviens nelasa).
3. **Datu labojums** 9 atgrieztajām rindām pa vienai pēc `fix_links_2026-10-05b.py` / `rollback_doc90310_…` nodoma (trigeri ieraksta apspiešanu); 7 pāriem ir pozīcijas — operators redz sarakstu pirms rakstīšanas.
4. **Vēsture — NEsēt 4 217 rindas tagad** (Astra: «vēsturiska prombūtne nav vēsturisks nodoms»; `_d2_scope.py` norij kļūdas, neatšķir neizpildītus labojumus). Tā vietā audits (d) periodiski skaita «noņemts rollback faila forward kopā, tagad atkal DB» ar `_d2_scope` metodi (pēc kļūdu skaita drukāšanas labojuma) — kandidātu saraksts, ne automātiska apspiešana. Verificētas grupas var iesēt vēlāk ar pārskatītu manifestu un precīzu rollback (pēc ID, ne `LIKE`).
5. **Audits** `scripts/audit_integrity.py`: (a) neatcelta apspiešana, kuras trīskāršs IR junction (sagaidāms 0); (b) [info] atcelšanas pēdējās 14 d — katrai jāatbilst operatora rollback; (c) [info] apspiešanas, kuru doks pārielādēts pēc apspiešanas (`scraped_at` LV pret `created_at` UTC — salīdzina ar `DATE(created_at,'localtime')`), — iespējams likumīgs atgriezums; (d) skat. 4. soli.
6. **Dokumentācija**: CLAUDE.md «A full `rescan_all` re-adds false links…» → jaunais noteikums; `/seed-entity` un rollback-ģenerators (slēdzis); CHANGELOG.

## Nesaskaņas starp pārskatītājiem
- Astra ilgtermiņā iesaka DB līmeņa `RAISE(ABORT)` + skaidru atcelšanu rollback failos; advisor un plāns — automātisku atcelšanu ar pierādījumu (`lifted_at`), jo 87 vecie rollback faili jāpalaiž bez izmaiņām. Kompromiss: ABORT var ieslēgt vēlāk, kad rollback ģenerators raksta atcelšanu pats.

## Ārpus tvēruma
588 pāri ar `subject`+`mentioned` — atsevišķa audita pārbaude un triāža.
