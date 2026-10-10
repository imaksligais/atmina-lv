# Handoff 2026-10-05 — dienas rutīna, pēcpusdiena (soļi 1–4)

## PUBLICĒTS 20:50 — deploy `abd491a7`, rutīna 11/11 ✓

Pēc operatora atļaujas: attēls #361 apstiprināts, `approve_publish 2026-10-05`, renders (12 domēni), HTML pārbaudīts (2 kastītes kā saraksti, labojumi iekšā), deploy, `verify_host` 9/9, attēlu varianti live 4/4 HTTP 200. Operatora lēmumi (commit 09f6d0db, rollback `data/rollback_operator_2026-10-05.sql`): #730611 un #730593 → `Izvērtēts 2026-10-05:`; Līdakas #730604 dzēsts; Levrence role → «15. Saeimā ievēlēta — PRO»; 22 veci spriežu priekšlikumi (#206–226, #231) noraidīti. `.scratch/2026-10-05-db-kopijas` (11 GB) dzēsts.

Atvērts (nav darīts): wiki salauzta saite Vaidere → Rosļikovs (neaktīvs, `src/wiki.py` nevajadzētu saistīt uz neaktīviem); `parties.coalition_status` jāmaina dienā, kad sanāk 15. Saeima; `/audit-integrity` (651213, 655623, pretruna #27); lomu inversijas → `backlog/matcher.md`; skeleta sīkumi (SV-AJ/SV/AJ, tēmu secība, pmo.ee/tvnet.lv) `src/briefs.py`; Urbanovičs — gaidīt; 2b: 2 Stepaņenko doki. **Morozs (starpība 7) un Plaude (15), SV/AJ** — operators 10-05: gaidīt CVK oficiālo sarakstu (CVK apstiprina līdz **2026-10-19**; `dati.cvk.lv/SV2026/ieveletie-deputati/` 10-05 vakarā vēl 404), tad diff visiem 100 pret `data/cvk_sv2026_ievēlētie.yaml`.

### (vēsturiski) Publicēšanas soļi, kā bija sagatavoti
1. Attēls #361: `.venv/Scripts/python.exe -c "from src.db import get_db; from src.graphics.storage import approve_image; db=get_db('data/atmina.db'); approve_image(db, 361); db.commit()"`
2. `.venv/Scripts/python.exe scripts/approve_publish.py 2026-10-05`
3. `.venv/Scripts/python.exe -m src.render --only=dashboard,static,blog,persons,topics,parties` → variantu vārti (a) no `/dienas-rutina` → `bash scripts/deploy.sh --dry-run --no-delete` → `bash scripts/deploy.sh --no-delete` → `verify_host.py` + variantu vārti (b). Variantu vārtos `DAY='2026-10-05'` arī pēc pusnakts.
4. **Pēc rendera, pirms deploy, izlasi `output/atmina/blog/2026-10-05.html`.** Abām konteksta kastītēm (#677, #678) jārādās kā sarakstiem, Lead 4. punktam — sadalītam. Būvē pašlaik ir VECĀ versija (pirms QA labojumiem). Ja preflight atsaka, NEKAD nelieto `--no-output-check`.
5. Kamēr nav deployots, nedari `git push` / publiskā spoguļa sync (`wiki/dailies/2026-10-05.md` ir melnraksts).

Izdarīts vakarā:
- **Ielāde** 19:35–20:00 (`logs/ingest_2026-10-05_vakars.log`), 5/5 OK, `shadow`; TypeSafe judged 581 / vetoed 13 (backlog/dati-db.md).
- **Ekstrakcija:** 9 aģenti / 3 kārtas / 73 pāri → 73 apstrādāti; atgūšana 22 pāri → 22; atkārtoti plāns = 0, apsekojums = 0. **25 jaunas pozīcijas 730620–730644** (dienā kopā 65).
- **Medības** 25 pozīcijām: 1 kandidāts (Indriksone 730316↔730642) → devils-advocate KILL; `log_action` ar 10 `rejected_candidates`.
- **Spriedzes:** 34 priekšlikumi; šodienas 13 izvērtēti (5 pieņemti #441–445, 8 noraidīti) + 3 manuāli (#446 Šlesers→Kulbergs, #447 Vaidere→Rosļikovs, #448 Šlesers→Siliņa). **21 veci priekšlikumi (tvīti 2025-11…09-30, #206–226, #231) atstāti `pending`** — operatora lēmums, vai tos reģistrēt.
- **Piezīmes:** #677 (Koalīcija), #678 (Vēlēšanas / partiju finansējums).
- **Pārskats #679** (brief-writer) → quality-reviewer BLOCKED (3 faktu, 7 pēdiņu, stila labojumi) → visi ieviesti ar rollback `data/rollback_qa_teksts_2026-10-05.sql` (commit 4696b166), 6 pozīcijām reembed; lint 0. `wiki_sync` + `wiki/dailies/2026-10-05.md` (commit f7ca8f6c). `check.sh`: 3326 passed.
- Operatoram papildus: Abu Meri #730611 `NEEDS_REVIEW` faktu apstiprina 6 avoti — var izvērtēt; «Stabilitātei!» `coalition_status=opposition`, bet partija nav Saeimā (pārbaudīt); Čulkova par Rosļikova neatgriešanos (doks aiz #730631) pret solījumu #704157 — iespējams pāris, claim nav izvilkts.

> **Vakara sesijai:** otrā (vakara) ielāde → ekstrakcijas delta → soļi 5–7 → pārskats. Pārskats NAV rakstīts (operatora lēmums: pēc otrās ielādes). Nekas nav deployots.

## Izdarīts

- **Ielāde** 16:02–16:35 (`logs/ingest_2026-10-05_pecpusdiena.log`), 5/5 soļi OK, TypeSafe `shadow`. Twitter: zināmās twikit `KeyError: 'value'` pa vienam kontam (tādas pašas rītā) — nav fatālas.
- **1b Vēstnesis:** 0 paraksta-pāru — nav ko rakstīt.
- **Ekstrakcija:** plāns 27 aģenti / 5 kārtas / **197 pāri → 197 apstrādāti** (aģentu atskaišu summa = plāns; pēc tam `plan_extraction.py` = 0 pāru). Atgūšana (`recovery_survey`, josla `beside_subject`): 24 pāri → 2 aģenti, 24 apstrādāti, atkārtots apsekojums = 0.
- **Jaunas pozīcijas: 40, id 730580–730619** (35 ekstrakcija + 5 atgūšana); 14 ar `NEEDS_REVIEW` (īsi tvīti, atstāsti). Trīs pāri dokā 124191 (pid 18, 72, 183) aizvērti ar roku (`empty_doc_ids`; pozīcijas jau bija 10-04).
- **Pretrunu medības** visām 40: 2 `contradiction-hunter`, **0 kandidātu, 17 noraidīti** (`logs` `contradiction_hunt` `date=2026-10-05` ar `rejected_candidates` → panelis «Pretrunu kandidāti»). Devils-advocate — nav ko pārbaudīt. Rutīnas 3. solis ✓.
- **Stepaņenko X konts `@StepanenkoJulij` strādā:** 10-05 ielāde ievāca 17 viņas konta tvītus (`documents.source_url`), seed handoffa punkts slēgts.
- **TypeSafe ēna 10-05** pierakstīta `backlog/dati-db.md` (judged 961, vetoed 23; zelta zaudējumi: Kulbergs ×2, Krauze, Rosļikovs, Dombrovskis).
- **Sakārtots:** 10 izpildīti handoffi → `docs/arhivs/handoffs/` (atvērtie punkti → `docs/HANDOFF-2026-10-05-15saeima-seed.md` § «Pārcelts no arhivētajiem handoffiem»); saknes mapes vaļīgie faili (ignorēti, ne-git) → `.scratch/2026-10-05-saknes-faili/`.
- `check.sh` HEAD: 3326 passed, «all checks passed». (Pirmais skrējiens krita uz DB sarga — tas bija paralēlo aģentu rakstīšana testu laikā, ne testu kļūda; atkārtojums tīrs.)

## Vakara sesijai — secība

1. Otrā ielāde (fonā, ~20 min) → `plan_extraction.py --days 2` → dispatch → `recovery_survey.py --days 2`.
2. Medības tikai pozīcijām **id > 730619** (šīs 40 jau medītas; sweep 729966–730579 arī).
3. **5. solis Spriedzes:** `saites_proposals.py --days 1`, tad pārskatīt. Spriedzes meklēt šodienas pozīcijās (id ≥ 730580), ne sweep — `print_routine` rāda «138 politiķiem», jo ieskaita sweep.
4. **6. solis Konteksta piezīmes** (append-only, B forma ≤120 vārdi). Dienas tēmas: koalīcijas sarunas pēc tikšanās ar prezidentu (Kulbergs: ar LPV nē, mazākuma valdība iespējama, finanšu portfelis AS; Šlesers: AS+LPV «vēsturiska iespēja»; Siliņa: gatava sarunām AS vadībā), Abu Meri atkāpjas no JV domes priekšsēdētāja amata, partiju finansējums (Baško, Čulkova, Stepaņenko), Stepaņenko — Kleinberga atstādināšanas paraksti.
5. **7. solis Pārskats** — `@brief-writer`. Pateikt tam:
   - skeletā (created_at zars) iekrīt 15 backloga pozīcijas ar `stated_at` 09-28…10-03 (#730002, 730003, 730016, 730040, 730067, 730088, 730163–730166, 730256, 730257, 730259, 730298, 730315) — tas ir backlogs, ne 10-05 ziņas;
   - #730586 (Stepaņenko, `stated_at` 2026-08-27), #730604 (Līdaka, 2025-11-02), #730608 (Āboliņš, 09-15) — veci tvīti, nav dienas ziņas;
   - «Deputāti 179» un personu filtrs «15. Saeima» jau live (deploy `12269d54`).
6. Quality gate → `@quality-reviewer` (§ H korektūra) → attēls → operatora atļauja → `approve_publish.py` → render (`dashboard,static,blog`, + skartie) → deploy.

## Operatoram (lēmumi / pārbaudes, nav darīts)

- **Urbanovičs (pid 232):** doc 124251 — «vairs neredz sevi «Saskaņā»», pametīs tās vadību. `party`=«Saskaņas Centrs» NEmainīts (T6 — pārbaudīt, vai izstājas no partijas, vai tikai no vadības).
- **Levrence (pid 54):** `role`=«Bijusī 14. Saeimas deputāte», bet doc 125761 — ievēlēta 15. Saeimā (stale, T6).
- **MMN izslēgšanas:** Baško tvīts 125854 — valde lems par biedru izslēgšanu (vārdi nav nosaukti); pēc lēmuma pārbaudīt `party`.
- **Braže #730593** (`NEEDS_REVIEW`, tvīts 1/2 pārtrūkst) — pamatojums ir 2/2 retvītā 125853 («Putins izdarīs visu, lai Ukrainu salauztu…»); ieteikums: atstāt stance, `reasoning` papildināt ar norādi uz 2/2 (izvērtēšana = `Izvērtēts YYYY-MM-DD:`).
- **Līdaka #730604** — avots ir Hirša tvīts, kas citē Līdaku (sekundārs, `NEEDS_REVIEW`); izlemt paturēt vai dzēst.
- **Datu defekti (medību atradumi, nelaboti):** claim 651213 (Līdaka `saeima_vote`) piesaistīts balsojumam 7431 (termiņš 01.11.2026), bet stance apraksta 1057 (1. lasījums 52:0) — `/audit-integrity` per-vote paritāte; claim 655623 (1141/Lp14) virsraksts «steidzamība», kopsavilkums «2. lasījums 90:1:1», ST frakcija 8 Pret.
- **Lomu inversijas (nelabotas):** Abu Meri dokos 125775/125808/125829 `mentioned`, bet raksts ir par viņu; R. Šlesers (pid 56) `subject` 5 dokos, kur tikai pieminēts (124194 u. c.) — T1 klase, `backlog/matcher.md`.
- **2b:** 2 veci pāri (zem sliekšņa 20) — vakarā pārbaudīt, vai paliek.
- **`.scratch/`** 11 GB DB kopijas (`2026-10-05-db-kopijas/`) — dzēst, ja vairs nevajag.
- Vecāki atvērtie punkti: `docs/HANDOFF-2026-10-05-15saeima-seed.md` (CVK oficiālais saraksts, Morozs/Plaude, «Šleseri», Lūses `negative_patterns`, pārceltie punkti).
