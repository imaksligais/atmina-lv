# Handoff 2026-10-06 — dienas rutīna (vakars)

## PUBLICĒTS 22:31 — deploy `5652328a`

Operatora lēmums: publicēt, Šmita #730684 dzēst (rollback `data/rollback_delete_730684_2026-10-06.sql`), spriedzes priekšlikums #242 noraidīts, pretruna #54 paliek `confirmed=0`. Pirms deploy `check.sh` 3341 passed; attēls #362 apstiprināts; `approve_publish 2026-10-06`; renders (10 domēni); varianti 4/4 uz diska; `verify_host` 9/9; varianti live 4/4 HTTP 200; `blog/2026-10-06.html` 200. Šmita tvīts (doc 126840) apzināti paliek cilnē «X ieraksti» (Šmits + Stendzenieka RT) — tas ir viņa paša publisks ieraksts. `git push` / spoguļa sync NAV darīts.

## Izdarīts

- **Ielāde** 20:47–21:20, vienīgā dienā (rīta nebija) — `logs/ingest_2026-10-06_evening.log`, 5/5 OK, `shadow`; 17 X kontiem ReadTimeout, 1 KeyError (D_Straubergs) — nefatāli. TypeSafe: judged 225 / vetoed 6 → `backlog/dati-db.md`.
- **Vēstnesis:** 9 paraksta-pāri atzīmēti (rollback `data/rollback_vestnesis_stamp_2026-10-06.sql`).
- **Ekstrakcija:** plāns 27 aģenti / 4 kārtas / 208 pāri → 208 apstrādāti (+3 veci 2b pāri, 0 pozīciju); atgūšana 26 pāri → 26. Atkārtots plāns = 0, apsekojums = 0. **79 pozīcijas 730645–730723.**
- **NEEDS_REVIEW:** 12 → 5 izvērtēti ar advisor padomu (730651, 730671, 730687, 730693, 730710; rollback `data/rollback_review_2026-10-06.sql`), **7 operatoram** (zemāk). Rinda: 235 atvērtas, 0 > 14 d.
- **Medības:** 79 pārbaudītas, 1 atrasta — **#54** Kulbergs, «Netflix» nodeva (548010 ↔ 730699, `reversal`), devils-advocate **KEEP**, `reviewed=1`, `confirmed=0`. 21 `rejected_candidates` žurnālā.
- **Spriedzes:** #449–452 pieņemtas, #238 un #244 noraidītas, #453 manuāla (Puntulis↔Kulbergs). **#242 (Šmits→Patmalnieks) atstāts `pending`** — operatoram.
- **Piezīmes:** #680 (Koalīcija), #681 (Izglītība).
- **Pārskats #682** → QA BLOCKED → labots (`data/rollback_qa_teksts_2026-10-06.sql`, `..._qa_teksts2_...`, `rollback_stance_730656_...`), pārembedēti 730645, 730655, 730656, 730671, 730700 → QA PASS ar nosacījumu (izpildīts) + 1 saskaņojums pēc pārbaudes (730656 stance = tabulas teksts). Lint 0. `wiki/dailies/2026-10-06.md` = DB.
- Sīki labojumi: 730649 «húsiju»→«hūsītu», 730705 citāta beigas (abi ar rollback).
- `check.sh`: 3341 passed, 3 skipped. `wiki_sync` ✓. `print_routine`: 1–7, 9, 10 ✓; 8 ✗ = attēls gaida apstiprinājumu; 11 ◐ = nav deployots.

## Operatoram — lēmumi

1. ~~Publicēt~~ — izdarīts (sk. augšā). Vēsturiski soļi:
   0. `CHECK_PYTEST_WORKERS=3 bash scripts/check.sh` (zaļš bija PIRMS QA teksta labojumiem un 5 pārembedingiem)
   1. `.venv/Scripts/python.exe -c "from src.db import get_db; from src.graphics.storage import approve_image; db=get_db('data/atmina.db'); approve_image(db, 362); db.commit()"`
   2. `.venv/Scripts/python.exe scripts/approve_publish.py 2026-10-06`
   3. `.venv/Scripts/python.exe -m src.render --only=dashboard,static,blog,politiki,personas,temas,partijas,pozicijas,pretrunas,spriedzes` → variantu vārti (a) ar `DAY='2026-10-06'`
   4. `bash scripts/deploy.sh --dry-run --no-delete` → `bash scripts/deploy.sh --no-delete` → `verify_host.py --base https://atmina.lv` → variantu vārti (b)
2. ~~#730684 Šmits~~ — dzēsts. — publisks vēlējums, lai prokuratūra celtu apsūdzību Patmalniekam. `review_status` NEBLOĶĒ renderi: pēc nākamā `personas`/`politiki` deploy tas parādīsies Šmita profilā. Paturēt / dzēst — izlemt PIRMS deploy. Tas pats spriedzei #242.
3. Pārējie 6 NEEDS_REVIEW: 730657 Pūpols (apzīmējums par @irLV), 730690 Brēmanis («atgrieziet zeltu», 09-29), 730691 Zalāns («SK»/«P»), 730653 Baško (NRA sleja), 730682 Kulbergs (pateicības tvīts), 730680 Patmalnieks (saite neatšifrējama).
4. **Pretruna #54** — publicēt (`confirmed=1`) vai nē.
5. Brēmaņa tvīts 126882 (apsūdzība nosauktai personai) apzināti atzīmēts kā tukšs.

## Atvērtie punkti (nelaboti)

- **Jautājums: vai skeletam jāfiltrē `review_status`?** Pārskati pēc noteikuma filtrē tikai `claim_type`; 10-05 pārskatā bija NEEDS_REVIEW pozīcijas. Šodien 7 neizlemtās izņemtas no #682 ar roku — piesardzīga izvēle, ne noteikums.
- ~~Datu defekts 651239/651192~~ — NAV defekts: māsas balsojumu kopsavilkuma konvencija (operatora lēmums 2026-08-17/18, `src/saeima/votes.py::generate_claims_from_votes` docstring) — `summary` pieder likumprojektam, vēsturiskās rindas netiek pārrakstītas. Nelabots apzināti.
- Lomu inversijas: Pujāts (pid 246) `mentioned` 4 dokos, kur runā pats; Rinkēvičs 126730 → `backlog/matcher.md`.
- Party-change: Štāls (pid 173) — JKP apsver likvidāciju/zīmola maiņu (lēmuma nav, T6).
- Lieki `analyses` ieraksti 12304, 12329–12332 (atkārtoti izsaukumi, nekaitīgi).
- Wiki salauztā saite Vaidere → Rosļikovs (no 10-05).

## NEEDS_REVIEW masveida triāža (vakarā, operatora lēmums)

Rinda 234 → 1 (atvērta paliek 689653 Lapsa — jāpārbauda video). 65 dzēsti (A smagi apgalvojumi 13, B nav paša vārdi 21, C nogriezts/vecs avots 15, D maz satura 16), 168 → `Izvērtēts 2026-10-06:`. Rollback `data/rollback_needs_review_triage_2026-10-06.sql` (ar vektoriem). Deploy `6efdc3f6`, `verify_host` 9/9.
Paliek operatoram: (1) oriģinālie tvīti joprojām cilnē «X ieraksti» un `x.html` (dokumenti nav dzēsti); (2) publicētajā pārskatā `blog/2026-10-01` tabulā ir Stendzenieka dzēstā pozīcija («psihiski slimi…») — labot publicētu pārskatu vai nē.
- **Pārskatīts:** A grupas 13 pozīcijas atjaunotas (operatora standing lēmums — asums nav iemesls dzēst; CLAUDE.md § Standing Decisions), statuss `reviewed`; rollback `data/rollback_restore_A_2026-10-06.sql`. Deploy `7b827c47`, `verify_host` 9/9. Tātad dzēsti paliek 52 (B 21, C 15, D 16). Punkts par `blog/2026-10-01` vairs nav aktuāls.
