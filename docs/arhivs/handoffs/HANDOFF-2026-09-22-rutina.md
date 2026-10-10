# HANDOFF — dienas rutīna 2026-09-22

Rutīnas diena **2026-09-22** ir pabeigta un publicēta (`print_routine()` → 10/10 ✓). Šis fails ir nākamās sesijas sākumpunkts; lēmumi ir `wiki/CHANGELOG.md` 2026-09-22 (8), atvērtais darbs `backlog/dati-db.md` § 2026-09-22 rutīnas atlikumi.

## Kas izdarīts

| Solis | Rezultāts (saucējs) |
|---|---|
| Ingest | `scripts/morning_ingest.py` 5/5, 786 jauni doki (RSS 147, Vēstnesis 19) — palaists tikai 22:05, rīta ielāde nebija notikusi |
| Pozīcijas | 64 politiķi / 220 doki → 35 `@claim-extractor` aģenti + 2 secīgi sweep (Braže 3×, Kulbergs 2×) + 3 junction-atgūšanas aģenti (30 pāri) → **79 pozīcijas** (id 717845–717923), 32 `NEEDS_REVIEW`, 0 `failures` |
| Pretrunas | `@contradiction-hunter` 79 pārbaudītas → 1 kandidāts, 7 noraidīti (`logs.id=655410`); `@devils-advocate` SURVIVE → **#53 Kulbergs publicēta** (`minor_shift`, operatora lēmums) |
| Spriedzes | #354–#358 ar roku (TypeSafe 402), pēc apmaksas `saites_proposals` 11 priekšlikumi → 4 pieņemti (#359–#362), 7 noraidīti (dublikāti / nepareizs mērķis) |
| Piezīmes | #633 Ukraina un Krievija, #634 Imigrācija, #635 Valsts pārvalde (B forma, ≤120 vārdi) |
| Pārskats | #636, `@quality-reviewer` 1. kārta BLOCKED (2 faktu kļūdas mūsu tekstā) → 2. kārta PASS; attēls `brief_images.id=341` apstiprināts; `publish_approvals` 2026-09-22 |
| Deploy | 4 deploy (pārskats; #717922 tēma + #53; Francijas konteksts + spriedzes; pretrunu sadaļa pārskatā), katrreiz `verify_host` 9/9, varianti 4/4 live 200 |

## Koda izmaiņas (commit `b3848d8a`)

- `scripts/check.sh` smoke ietver `static` — citādi katrā jauna pārskata dienā `check_output` krita uz sitemap.
- `scripts/typesafe_veto_report.py` — `exit 2` «NO EVIDENCE», ja logā nekas nav novērtēts. Tā diena ēnas nedēļā neskaitās.

## Datu labojumi ar rollback (visi `data/rollback_*_2026-09-22.sql`)

`needs_review_conf06` (7 claims), `note633_trim`, `contradiction53_summary`, `brief_review_round1`, `lb717922_topic_c53_confirm` (#717922 Klimats→Vide + re-embed; #53 `confirmed=1`), `c53_france_brief_tensions`, `brief636_pretrunas`.

## Atvērts nākamajai sesijai

1. **TypeSafe ēnas nedēļa:** 2 zelta zaudējumi (Kučinskis 09-18, Alvis Hermanis 09-22) — abi «pareizā persona, nepolitisks konteksts». `enforce` nav pamatots, kamēr instrukcija šo klasi nešķir. 09-22 skaitās tikai pēc atkārtotās novērtēšanas (scored 97).
2. `backlog/dati-db.md` § 2026-09-22 rutīnas atlikumi (a)–(f): stance teksta labojumi, #704185/#717838, Ašeradena `role`, robežgadījumi, iespējams Saeimas 09-03 balsojumu robs, graphics variantu instrukcija.
3. Melbārdes `party` — kandidāts otrajam avotam doc 113334 (tas pats ieraksts, 08-25 (b)).
4. Vēstneša akts 1 no 19 (`print_routine` sadaļa) nav skatīts ar roku.
5. Sociālais pavediens par 09-22 nav rakstīts (`/social-thread`, gaida operatoru).

## Mācības (jau ierakstītas repo)

- Pretrunas kopsavilkumam jāietver abu avota dokumentu pilnais konteksts — 1. versijā trūka, ka nakts tvīts jau minēja Parīzi un ka pretī bija Francijas drošības piedāvājums; operators to pamanīja ar jautājumu «kāpēc viņš tā teica».
- `generate_daily_brief(db_path, date)` — pirmais arguments ir DB ceļš; `generate_daily_brief('2026-09-22')` izveido tukšu SQLite failu repo saknē (izdzēsts). Vienmēr `date=`.
