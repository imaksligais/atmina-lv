# atmina — CHANGELOG

Vēsturiskas datu modeļa un pipeline izmaiņas. Runbookiem un `CLAUDE.md` jāpaliek tīriem no datumu atzīmēm — jaunas izmaiņas loģē šeit un atsaucas no attiecīgā runbook vai invariant. Ieraksti līdz **2026-08-27** (ieskaitot) dzīvo [CHANGELOG-arhivs.md](CHANGELOG-arhivs.md); atsauktajiem ierakstiem šeit paliek enkuru-stubi (sadaļa "Arhīvs" faila beigās).

**Atšķelšanas noteikums.** Šis fails ir konteksta izmaksa katrai sesijai, kas to atver, tāpēc tas nedrīkst augt bez robežas. Slieksnis: **kad fails pārsniedz ~120 KB, atšķel vecāko pilno mēnesi.** *2026-08-05 ar operatora apstiprinājumu veikta agrīna daļēja atšķelšana (07-31→08-02, 22 ieraksti) — fails atgriezās zem 120 KB, un 2026-08-04 pagaidu izņēmums (~160 KB līdz 09-01) vairs nav spēkā.*

**Ieraksta garumu mēra BAITOS, ne rindās (labots 2026-08-22).** Līdz šim šeit stāvēja „sesijas ieraksts ≤ ~30 rindas". Tie bija vārti, kas nevar nokrist: 2026-08-22 mērījums deva **0 pārkāpumu no 54 datētajiem ierakstiem**, kamēr fails bija **144 957 B = 18 % pāri savam paša slieksnim**. Cēlonis ir vienkāršs — vidēji 341 zīme rindā, tāpēc formāli atbilstošs 30-rindu ieraksts ir 10,2 KB, un 2026-08-18 ieraksts ir 12 081 zīme tieši 30 rindās, t.i. **10 % no visa budžeta caur zaļiem vārtiem**. Skaitītājs mērīja rindas, budžets skaitīja baitus; tā ir tieši tā „gate that cannot fail" klase, ko `CLAUDE.md` aizliedz. Jaunā norma: **sesijas ieraksts ≤ ~4 KB** (aptuveni 12 vidēja garuma aizzīmes) — garāks pieraksts pieder CHANGELOG tikai kopsavilkumā, detaļas rollback/commit ziņām un `docs/audits/`. Mērī ar `awk '/^## 20/{if(n)print n": "c; n=$0; c=0} {c+=length($0)+1} END{if(n)print n": "c}' wiki/CHANGELOG.md | sort -t: -k2 -n | tail`. **Vēsturiskie ieraksti ir grandfathered** — tos NEsaīsina retroaktīvi (tā pati loģika kā 196 mantojuma `%` rindām § Ne-darīt: daļējs labojums būtu sliktāks par neko).

**Kad „vecākais pilnais mēnesis" vairs neeksistē, šķel vecāko pilno DIENU.** Kopš 08-02 atšķelšanas failā ir tikai viens (nepilns) mēnesis, tāpēc burtiskais noteikums nav izpildāms — 2026-08-09 ar operatora apstiprinājumu atšķelta diena **2026-08-03** (6 ieraksti / 38 KB; fails 110 → 71 KB). Iemesls šķelt pie 90 %, ne pie 100 %: **viena diena var pievienot 10 KB** — 08-09 sesija to izdarīja ar četriem ierakstiem, no kuriem neviens nepārkāpa toreizējo ≤30 rindu noteikumu. Toreiz no tā tika secināts, ka slieksni pārkāpj sesiju BIEŽUMS, ne ierakstu garums; **2026-08-22 mērījums to daļēji apgāza** — biežums ir viens dzinējs, bet otrs ir ieraksta baitu svars, ko rindu skaitītājs vienkārši neredzēja (sk. iepriekšējo rindkopu). Abi ir spēkā, tāpēc gaidīšana līdz 120 KB joprojām nozīmē šķelt reaģējot, ne plānojot. Procedūra: (1) atrodi ienākošās enkuru atsauces ar `grep -rn 'CHANGELOG\.md#' --include=*.md .` — tikai tām vajag stubu; (2) pārcel mēneša ierakstus arhīva augšgalā (arhīvs ir jaunākie-pirmie); (3) atjauno šo rindkopu un „Arhīvs" sadaļas diapazonu; (4) pārbaudi, ka visi enkuri joprojām atrisinās. Līdzšinējās reizes kopā rāda, kāpēc 1. solis ir obligāts, nevis formalitāte: 2026-08-01 jūnija atšķelšanā **neviens** no 16 ierakstiem nebija atsaukts no citurienes, tāpēc stubi nebija vajadzīgi; 2026-08-02 jūlija atšķelšanā atsaukti bija **četri** no 33 (`CLAUDE.md` trīs vietās, `wiki/operations/ui-conventions.md` vienā), un bez stubiem tie enkuri vairs neatrisinātos; 2026-08-05 atšķelšanā atkal **neviens** no 22. Pārbaudi vispirms, nevis pieņem — abi iznākumi ir iespējami. 2026-08-19 atšķelta diena **2026-08-04** (3 ieraksti / 12,2 KB; fails 124 → ~112 KB). Enkuru atsauces uz 08-04 ierakstiem: 0 (pārbaudīts ar grep), stubi nevajadzīgi. **2026-08-23 atšķeltas piecas dienas 2026-08-05 — 2026-08-09** (16 ieraksti / 56,2 KB; fails bija 162,9 KB = 36 % pāri slieksnim, pēc atšķelšanas ~110 KB). **2026-08-24 atšķelta astotā reize: dienas 2026-08-10 — 2026-08-16** (8 ieraksti / 25,5 KB; fails bija 120 201 B = tikko pāri slieksnim, pēc atšķelšanas 94,3 KB = 79 % no sliekšņa). Šoreiz slieksnis tika pārkāpts ar **vienas sesijas ierakstu 3 853 B** — t.i. pat normai atbilstošs ieraksts var pārsviest failu pāri, ja tas jau stāv uz robežas; tāpēc atšķelts vairāk par vienu dienu, lai nākamās sesijas nesāktos ar to pašu darbu. Vienā dienā šoreiz nepietika: 08-05…08-08 kopā dod tikai 35,8 KB, tāpēc slieksni sasniedz vienīgi piecu dienu bloks — kad fails ieskrienas 36 % pāri, atšķelšana vairs nav vienas dienas darbs. Ienākošās enkuru atsauces uz JEBKURU 2026-08 ierakstu: **0** (`grep -rn 'CHANGELOG\.md#2026-08'` pār visu trekoto koku), tāpēc stubi nav vajadzīgi. **2026-08-27 atšķelta devītā reize: diena 2026-08-17/18** (1 ieraksts / 6,2 KB; fails bija 120 558 B — tikko pāri slieksnim pēc 08-26 rutīnas ieraksta). Ienākošās enkuru atsauces uz 08-17/18: **0** (`grep -rn 'CHANGELOG\.md#2026-08-1[78]'`), stubs nevajadzīgs. Pēc atšķelšanas ~114 KB = 95 % no sliekšņa — nākamā sesija, kas pievieno normas ierakstu, atkal būs uz robežas. **Tas notika tajā pašā dienā:** 08-27 sociālo postu sesijas ieraksts (3 299 B, normā) uzlika failu uz 119 763 B = 99,8 %, tāpēc tā pati sesija atšķēla **desmito reizi: dienas 2026-08-18 — 2026-08-19** (6 ieraksti / 20,5 KB; pēc atšķelšanas 99,3 KB = 83 % no sliekšņa). Divas atšķelšanas vienā dienā ir pats mērījums: pie ~10 KB dienā viena diena headroom nepietiek, tāpēc šoreiz atšķeltas divas dienas, ne viena. Ienākošās enkuru atsauces uz 08-18/08-19: **0** (`grep -rn 'CHANGELOG\.md#2026-08-1[89]'`, saucējs — 11 enkuru atsauces kokā kopā, visas uz 2026-04/2026-07 stubiem), stubi nevajadzīgi. **2026-08-27 vienpadsmitā atšķelšana — pirmā, kas šķeļ PROAKTĪVI, ne uz robežas: dienas 2026-08-20 — 2026-08-21** (13 ieraksti / 27,0 KB; fails bija 106 227 B = 88 % no sliekšņa, pēc atšķelšanas 78,0 KB = 65 %). Iemesls šķelt pie 88 %, nevis gaidīt: tās pašas sesijas ieraksts (~4 KB) un TĀS PAŠAS dienas vēl neizpildītā rutīna (~5–10 KB, mērīts pēdējās septiņās dienās) kopā uzliek failu uz ~92 %, tātad nākamā sesija sāktos ar šo pašu darbu — tieši tā forma, kuru 08-24 ieraksts jau nosauca par pusmēru. Vienpadsmitā reize ir arī pirmā, kur atšķelšanas iemesls ir ZINĀMS gaidāmais pieaugums, ne izmērītais pārkāpums. Ienākošās enkuru atsauces uz 08-20/08-21: **0** (`grep -rno 'CHANGELOG\.md#[a-z0-9-]*'` pār visu koku; saucējs — 9 unikālas atsauces, visas uz 2026-04/2026-07 stubiem), stubi nevajadzīgi. **2026-09-02 divpadsmitā atšķelšana, arī proaktīva: dienas 2026-08-22 — 2026-08-23** (8 ieraksti / 26,4 KB; fails bija 112 776 B = 92 % no sliekšņa pēc trim šīs dienas Saeimas ierakstiem, pēc atšķelšanas 83,7 KB = 70 %). Ienākošās enkuru atsauces uz 08-22/08-23: **0** (`grep -rno 'CHANGELOG\.md#2026-08-2[23]'` pār visu koku), stubi nevajadzīgi. **2026-09-05 trīspadsmitā atšķelšana: dienas 2026-08-24 — 2026-08-27** (12 ieraksti / 54,1 KB; fails bija 117 857 B = 98 % pēc astoņiem šīs dienas ierakstiem, pēc atšķelšanas ~64 KB = 53 %). Četras dienas, ne viena, jo 09-02 un 09-05 katra pievienoja ~20–25 KB — divu dienu headroom vairs nav pietiekams. Ienākošās enkuru atsauces uz 08-24…08-27: **0** (`grep -rno 'CHANGELOG\.md#[a-z0-9-]*'` pār koku; saucējs — 11 unikālas atsauces, visas uz 2026-04/2026-07 stubiem), stubi nevajadzīgi.

---

## 2026-09-08 (1) — 09-07 vakara rutīnas pabeigšana: pārskats publicēts, NEEDS_REVIEW rinda 0, divas korektūras pases

Vakara sesija 09-07 apstājās starp renderi (23:42) un attēlu; DB jau saturēja pilnu pārskatu #556, bet nekas nebija komitēts un `sitemap.xml` bija no 01:00, tāpēc `blog/2026-09-07.html` tajā nebija. Šī sesija pabeidza 8.–10. soli.

- **NEEDS_REVIEW triāža 12 → 0** (`scripts/triage_needs_review_2026-09-08.py`, pāra rollback ar `INSERT`): #709165 (Patmalnieks «elektrovalsts» — sauklis bez instrumenta, mērķa un termiņa) DZĒSTS ar vektoru; #709151 citāts nomainīts uz tēmai atbilstošo verbatim teikumu (bija AfD/Trampa teikums zem tēmas «Imigrācija»); pārējās 10 izvērtētas. `stored_resolved == intended_resolved == 11`. Dokuments 103578 apzināti PALIEK — dzēsta ir atmina.lv sava apgalvojuma forma, ne publiskā posta spogulis profila X apakšcilnē.
- **Divas `@quality-reviewer` pases, abas ar saucēju.** Pirmā: 7 labojumi (1 faktu kļūda — «vienīgā balss ārpus koalīcijas» ignorēja Pūci, kas ir `not_in_saeima`; 1 neitralitātes robs — VID 09-07 publiski noliedza daļu Pujāta apgalvojuma, ko pārskats nesa bez pretargumenta; 2 nepilnīgi skaitļi; gramatika; pēdiņu zīmes; lasāmība). Otrā, pēc labojumiem: PASS, plus viens atradums — Aizsardzības kastīte zem «Archer» virsraksta uzskaitīja Kulbergu, kura pozīcija ir par **IT** iepirkumiem pēc vētras; aizzīme precizēta pārskatā (piezīme #551 NEskarta — append-only).
- **Labojumi 5–6 aizvesti līdz pašām pozīcijām**, ne tikai pārskatam: `claims.stance` #709108, #709128, #709175 + re-embed (`audit_vector_staleness` pēc: `checked=3 match=3 stale=0`). Pārskata teksts un `claims.stance` citādi būtu klusi izšķīrušies.
- **§ H korektūras saucējs:** 91 prozas rinda + 164 tabulu teikumi izlasīti, ne izlase. **Mutācijas tests: 3 iesētas kļūdas, lints noķēra 2** — locījuma kļūdu (`pret valdība`) neredz, tāpēc `lint_lv_style()` = 0 viens pats par gramatiku neko nepierāda. Garuma jautājums (57,6 KB pret 22,4 KB 09-06) atbildēts ar mēru: 108 tabulu rindas pret 49 un 10 spriedzes pret 5, bet prozas blīvums uz rindu **zemāks** (102 pret 121) — apjoms, ne pūšana.
- **Publicēts.** `brief_images` #317 `approved=1`, `publish_approvals` `2026-09-07`, renders `blog,dashboard,static,temas,politiki`, deploy `--no-delete`. Vārti (a) 4/4 varianti diskā; vārti (b) **pārbaudīti 4 URL, 200: 4, cits: 0**; lapas 5/5 = 200. Ar šo aizgāja arī vakardienas kodā stāvošais tēmas→profila `#pozicijas` labojums — pārbaudīts live (30 saites `/temas/imigracija.html`, forma `…?tema=…#pozicijas`).
- **`wiki_sync()`** 489 lapas, `stale` 47 → 0. `check.sh` 2 549 zaļi; `check_output` sitemap 956 `<loc>` == 956 indeksējamas lapas (robs aizvērts). Jauna BACKLOG rinda: LSM slug dreifs (`a662064` divās `documents` rindās → divas saites uz vienu rakstu).

## 2026-09-07 (13) — Stāvokļa apskats pirms rutīnas: tēmas→profila `#pozicijas`, 13. pārbaude bez `saeima_vote`, 21 vektoru re-embed, nedēļas § 1/§ 4 mērījumi

Trīs read-only Opus aģenti (DB stāvoklis · backlog/handoff doki · kods+deploy) pirms 09-07 rutīnas; galvenie skaitļi ar vaicājumiem ir aģentu ziņojumos, šeit — kas mainījās. **(1) Tēmas lapa → profils atvērās Pārskatā, ne Pozīcijās** (operatora novērojums): `tema.html.j2` un `topics.py` «Turpini rakt» saites nesa `?tema=` bez `#pozicijas`, bet `ppv1.js` cilni ņem no hash. Abas vietas tagad `…?tema=<tēma>#pozicijas`; `tests/test_topics.py::test_profile_links_carry_the_tema_param_and_pozicijas_hash` prasa parametru UN hash katrai profila saitei (saucējs ≥2). Profili bez pozīcijām tēmas lapā neparādās pēc konstrukcijas (saraksts nāk no `claims`), tāpēc mirušu saišu nav; dokumentiem tēmu nav — tēma dzīvo tikai `claims.topic`. **(2) 13. pārbaude (`audit_vector_staleness.py`) izslēdz `saeima_vote` no kandidātu kopas** un ziņo `saeima_vote_izslēgti=N`: 09-07 sweep deva `checked=355 stale=171` (kontrole 25/25), no tiem 150 balsojumi — verdikts 2026-08-21 tos aizliedz pārrēķināt, tāpēc audits pats baroja rindas, ko labošanas rīks nedrīkst aiztikt. Testi: `tests/test_audit_vector_staleness.py` (+2). **(3) 21 `position` rindas re-embedotas** (`data/reembed_audit13_vectors_2026-09-07.ids`, rollback ar hex pre-image `data/rollback_reembed_audit13_vectors_2026-09-07.sql`): 16 ir `fix_drone_topic_boundary_2026-06-10` (Droni), pārējās marta–aprīļa topic/stance labojumi pirms 08-02 noteikuma; 08-04 bāzlīnija tos neredzēja, jo kandidātu parsers toreiz šo `IN (…)` formu nelasīja. Pēc apply: `checked=183 match=183 stale=0 saeima_vote_izslēgti=172`, exit 0. **(4) Nedēļas rutīna:** § 4 pilnais skrējiens `CHECK_PYTEST_MARKERS=""` — 2 549 zaļi (abi KNAB `slow` testi iet); vienīgais «error» ir ražošanas-DB sargs `_production_db_is_not_a_test_fixture`, kas noķēra paralēli ejošo `morning_ingest` (+47 dokumenti) — sargs neatšķir testu no fona ingest, **nelaid abus reizē**. Vote-result audits `mismatches=0`; `weekly-routine.md` § 4 novecojusī «salīdzini ar 562» instrukcija nomainīta uz gaidāmo 0. § 1 `weekly_cross_check(0.80)` izmērīts — 56 871 pāri, nav rinda → BACKLOG 53. **(5) Doku saskaņa:** BACKLOG 34 vienlaikus «noraidīts» un «sagatavots» — 105. rinda tagad norāda uz 09-07 pārmērījumu; `repo-higiena.md` CSP `--apply` ieraksts slēgts (bija izpildīts 09-06). Jauni operatora punkti 53–57 BACKLOG § Atliktais. **Nav deployots** — aiziet ar rutīnas renderu.

## 2026-09-06 (3) — Nedēļas pārskata forma pēc 10 nedēļu mērījuma: trīs skeleta rindas + valodas noteikumi rakstītājam

Operators: «bez bloat un slop, ar cilvēcīgu valodu». Mērījums pār 10 pēdējiem nedēļas pārskatiem (#299–#517): 813–2 359 vārdi bez mērķa; stāsts un tēmu sadaļas ar tām pašām saitēm (08-24: 3 no 3); semikolu virtenes un rāmji «sadalījās divās līnijās / trīs slāņi / smaguma centrs» katru nedēļu; `## Pretrunas` ar 40 vārdu «nekā nav» rindkopu 9 nedēļās no 10; `[x.com](…)` etiķetes (16 vienā pārskatā); teikums zem koalīcijas tabulas, kas atkārto tabulas skaitļus; neviena saite uz dienas lapām.

- **Skelets (`generate_weekly_brief`, 3 rindas, `tests/test_briefs_weekly.py` +5 testi):** (1) `**Pārējās tēmas:**` rinda — tēmas ārpus top-4 ar ≥3 pozīcijām nosauktas, aste ar 1–2 pozīcijām salocīta vienā skaitā (dzīvajā nedēļā 55 tēmas → ~10 nosauktas + skaits; agrāk 5.+ tēma pazuda, T7 analogs nedēļai); (2) `## Pretrunas` tabula tikai ar apstiprinātu rindu nedēļas logā — nulle paliek statistikas kartītē; (3) `**Dienu pārskati:**` — nedēļas dienu saites `/blog/YYYY-MM-DD.html` tikai dienām ar `publish_approvals` rindu UN dienas pārskatu pēc subjekta datuma (nepublicēta diena = 404). `by_topic` vairs nav `LIMIT 7`. Nedēļas dienas etiķete no kalendāra (`weekday()`), ne cikla indeksa — testa fikstūra sākas otrdienā, un tas noķēra kļūdu pirmajā palaidienā.
- **Rakstītājs (`.claude/agents/weekly-brief-writer.md`):** mērķis 1 000–1 400 vārdi; viens fakts vienā vietā (neviens `source_url` divās sadaļās); tēmas bloks = treknraksta teikums + rinda uz runātāju ar saiti tajā pašā rindā, `Avoti:` astes aizliegtas, `[x.com](` = 0; zem tabulas tikai tas, kā tabulā nav; `Skats uz priekšu` tikai ar datētu notikumu; aizliegto rāmju saraksts; pašpārbaude ar četriem skaitļiem. `quality-bars.md` § Nedēļas pārskats +2 rindas.
- **Blakus:** `BACKLOG.md` agenti-pipeline indekss 15 → 16 (09-06 ieraksts `get_pending_politicians(days=1)` bija failā, ne indeksā; `test_backlog_index_sync` krita tīrajā kokā).

## 2026-09-06 (2) — Operatora lēmumi pēc rutīnas: E1 demotēšana, Zīles veto, pirmais `csp --apply`, sešas `needs_review` rindas

Operators izvēlējās 1, 2, 4, 7 no septiņām atvērtajām rindām (3 name_forms noraidīts, 5 citātu triāža un 6 video atlikti). Katram — fix + pāra rollback `data/`.

- **E1 (verdikti 36+38, vēsture).** `fix_grupaE_subject_demote_2026-09-07.sql` piemērots: releja slotu `subject` 2 993 → 0, biroja balss RT → 0. **Faila `had_mentioned_twin` karogi bija 09-07 momentuzņēmums — 3 pāri (101015, 101044, 101733 × LETA) pa dienu bija ieguvuši `mentioned` dvīni** (web doks pārrakstīts, jaunais vārts rakstīja `mentioned`), un UPDATE tiem kristu ar UNIQUE, apturot visu transakciju. Papildinājums `fix_grupaE_subject_demote_addendum_2026-09-06.sql` tos dzēš; galvenajā rollback šie 3 pāri izņemti, atjauno addendum rollback. Dubultpāri korpusā 3 376 → 3 278 (95 + 3). Mācība: sagatavots datu fails ar iepriekš aprēķinātiem stāvokļa karogiem novecojas ar katru ingest — pirms izpildes karogus pārrēķina.
- **Zīle (verdikts 31).** `negative_patterns` pid 21 = KVC vadītāja amata frāze (abi reģistri); plus otra mutācija `fix_grupaD_zile_junction_2026-09-06.sql` — 2 Arvja Zīles junction rindas (doc 39, 93457; 0 claims) dzēstas.
- **CSP (49b).** `python -m src.csp --apply`: 10/10 tabulu, `csp_data` 1 481 → 1 509, atsevišķs commits `562b4ca8`. **Runbooka robs:** statistikas lapas deploy iet no `curated/atmina/` overlay — `--apply` viens pats live neko nemaina, un pilns renders svaigo izvadi pārraksta ar veco. Momentuzņēmums atjaunots no `generate_statistika()`, `render_baseline_misc.json` pārģenerēts (statistika hash ir tur), live md5 == lokālais, 11 faili. Procedūra tagad `commands.md` § CSP.
- **needs_review (7).** `fix_needs_review_2026-09-06.sql`: #709086, #709088, #709090, #709096, #709098 → «Izvērtēts 2026-09-06» (trigeris → `reviewed`); **#709106 (Štekerhofs) dzēsta** — rakstā viņš nerunā, rinda balstījās uz komisijas balsojuma faktu. Doc 90283 paliek ar `reviewed_at`. Atvērtā rinda 61 → 55. Tendence #545 un pārskats #546 (jau publicēts) Štekerhofu joprojām piemin kastītē kā balsojuma faktu ar atrunu — tas ir LSM fakts, ne pozīcija, tāpēc atstāts. Štekerhofa profils pārrenderēts un deployots (live 0 atsauču uz #709106).

## 2026-09-06 (rutīna) — 09-06 rutīna publicēta: 25 pozīcijas, 0 pretrunu, pārskats #546; deviņas handoff pārbaudes ar mērījumu

Pirmā rutīna pēc 09-06 verdiktu izpildes (`docs/HANDOFF-2026-09-08-rutina-pec-verdiktiem.md`). Ielāde 20:10–20:27 LV (5/5, 460 doki: 61 web, 196 twitter, 203 x_mention, 0 Vēstnesis). Ekstrakcija 16 paralēli `@claim-extractor` (12 solo ≥3 dokiem, 4 kopīgi ≤2 dokiem) + 1 junction-atgūšana: 33 politiķi / 88 doki → 25 pozīcijas (#709083–#709107, 13 politiķi), 6 `needs_review`, `failures=[]` visos 24 `save_analysis()` izsaukumos, 4 ±5 d dublikāti izlaisti (102433, 102454, 102430, 102428). Pretrunas 0 no 25 (`contradiction_hunt` ar 13 `rejected_candidates`). Spriedzes #267–#271, tendences #543–#545, pārskats #546 + attēls #314 (`image_audit` #317). Deploy 22:1x LV; live 4/4 varianti 200.

**Handoff pārbaudes (visas deviņas):**
- Ingest rinda «Nogriezts ievads: 0 no 63 web dokiem» ir; diena.lv deva 4 dokus, 0 nogrieztu — nav aizdomīgs.
- **pid 195 `subject` vārts: handoff vaicājums (pēc `scraped_at`) deva 3, ne 0 — bet visas trīs rindas rakstītas 09-04/09-05 pirms labojuma; web doki tika pārrakstīti (URL-first UPDATE reseto `scraped_at`), un šodienas ceļš tiem pievienoja `mentioned`. Pēc `created_at`: 0 no 99 šodien rakstītām `subject` rindām ir LETA, 0 biroja balss RT.** Vārts stāv; vaicājums jālasa pēc `created_at`, jo `scraped_at` web dokiem ir mainīgs. Blakus: PK `(document_id, politician_id, role)` pieļauj `subject`+`mentioned` vienam pārim — 3 376 tādi pāri korpusā, vēsturiskā demotēšana (BACKLOG § Atliktais) tos aizvērtu.
- pid 246/247: šodien 0 jaunu junction rindu (kopā 246: 9 subject/15 mentioned; 247: 2/7); Freifalta doki Toro (234) slotā — 0.
- «📜 VĒSTNEŠA AKTI» rinda: «0 no 0» — svētdiena, `stored=0` ir īsts.
- Confidence drift brīdinājums: klusē (n<5) — atbilst.
- pid 209 Štekerhofs: `get_pending_politicians(days=1)` doc 90283 (08-19) NEdeva — rinda ir dienas logā; apstrādāts ar rokas dispatch. Zīmogs 90283 sedz visus trīs (209 claim #709106 NEEDS_REVIEW — balsojuma fakts bez izteikuma; 126 Rokpelnis dublikāts pret #690470; 10 Kulbergs jau #703970).
- `review_status_at`: 6 no 6 jaunajām `needs_review` rindām NOT NULL — trigeris strādā.
- `image_audit` #317 `kind='brief'` 0,039 USD; mēnesis 0,624 → 0,663 — tieši par to.
- Live (Playwright, 390 px, `data-theme=dark`): sakļauts 13 čipi + «Vēl 20 tēmas»; klikšķis atver 32, poga pazūd; `?tema=Pensijas` uz sakļautu tēmu atver grupu un iezīmē čipu; 0 konsoles kļūdu.

**Krita un labots:** (a) `check.sh` — `test_render_chars.py::test_politiki_detail_pages_byte_identical` (3 profila hash) — commit 2f3fa0bc mainīja `src/render/politicians.py`, bet nepārģenerēja `render_baseline_politicians.json`; REGEN=1, 24/24 zaļi. (b) `@quality-reviewer` BLOCKED: spriedze #267 «tajā pašā dienā» nepatiess — Kulberga izteikums (#709098) ir TV3 atreferējums pēc 4. septembra ārkārtas sēdes, Zeltīta tvīts 09-06; labots 3 vietās (+ #268 «abi atbalsta» → «neviens nenoraida», § H teikums, Koalīcija/Opozīcija rindkopa) ar `data/rollback_tensions_267_268_brief_546_2026-09-06.sql`. (c) `/dienas-rutina` variantu vārta skripts glabāja PNG glob deploy kokā, kur renders kopē tikai variantus — `pamata PNG: 0` nokāva vārtu; skripts tagad lasa PNG no `output/images/briefs`, variantus no `output/atmina/images/briefs` (1 PNG / 4 varianti). (d) Handoff pre-deploy grep `pmo.ee` tēmu lapās deva 21, ne 0 — tas ir `href`, ne etiķete; redzamā etiķete `>pmo.ee<` = 0, `tvnet.lv ↗` = 2 (live). Atsauktās 4 pozīcijas live profilos: 0.

## 2026-09-07 (12) — NEEDS_REVIEW triāža: 55 → 0 (40 apstiprinātas, 1 pārkartota, 14 dzēstas)

Nedēļas rutīnas 5. solis (`weekly-routine.md` § 5), rinda bija 55 (7 augusta, 48 septembra).
Katra rinda lasīta pret avota dokumentu; verdikts operatora apstiprināts pa blokiem, forward
`data/fix_needs_review_triage_2026-09-07.sql`, pāra rollback ar pilnām dzēsto rindu INSERT kopijām
`data/rollback_needs_review_triage_2026-09-07.sql` (rakstīts pirms piemērošanas).

- **40 apstiprinātas** — marķieris → `Izvērtēts 2026-09-07:`; trigeris atvasināja `review_status='reviewed'`
  visām 41 skartajām rindām (kontrolvaicājums pēc piemērošanas: `reviewed 41`, `needs_review 0`).
- **1 pārkartota** — #709070 Žuravļevs «Latvija latviešiem» Imigrācija → Valsts pārvalde: ekstraktora
  paša pamatojums nosauca Valsts pārvaldi (imigrācija tekstā nav), bet glabātā tēma bija Imigrācija.
  Re-embed: `reembed_claims.py 709070` → `MAINĪJĀS`.
- **14 dzēstas** (703974, 704170, 704191, 704196, 704337, 704342, 704357, 706137, 706143, 706144, 706154,
  708990, 709048, 709058) — četras klases: stāvokļa ziņojums bez nostājas (Ķirsis «skolas gatavas», Hermaņa
  precedents 08-25); protokolārs tikšanās kopsavilkums (Dombrovska Kanāda/Dienvidkoreja/G20, Augulis,
  Patmalnieks); ceremoniāls vai sauklis (Rinkēviča Zinību diena un VAD apliecinājums, Ratnieka «prioritāte»);
  atribūcijas vai publicēšanas risks (Kulberga principi NRA atstāstā bez avota; Ceriņa «stepaņi, brēmšmaņi,
  čulkovi … slepkavu atbalstītāji» — antecedents ārpus dokumenta, smags apgalvojums par atpazīstamām personām;
  Kleinberga un NBS žurnālista pārstāsti ar conf ≤0,6). Pretrunu atsauču uz dzēstajiem 0; `claim_vectors`
  dzēsti līdzi. Dokumenti NAV dzēsti — profila X subtabs tos rāda joprojām (CLAUDE.md «claim deleted ≠ content removed»).

Robežu lēmumi, kas paliek precedentam: prezidenta formālie akti (komisiju sastāvi) glabājas kā pozīcijas
(#704343, pēc #689263/#20535); datu grafikas tvīts bez priekšlikuma ir derīga pozīcija (#704340, #709072 —
operatora lēmums 2026-09-05); politiķa paša retorisks apgalvojums par institūcijām glabājas ar atrunu
(#709024 Velps).

## 2026-09-07 (11) — Profila Pozīciju tēmu filtrs pārzīmēts: skaits, biežākās pirmās, «Vēl N tēmas» sakļaušana

Operatora karogs (ekrānuzņēmums no live 09-06): 33 tēmu čipu mākonis ar pilnu sarkanu aktīvo pildījumu profila Pozīciju cilnē izskatās neglīts. Pārzīmēts «Saites» cilnes filtra valodā (`.link-filter-btn` paraugs): punkts tēmas krāsā (`TOPIC_COLORS`), skaits katrā pogā (t. sk. «Visas tēmas 517»), secība pēc pozīciju skaita dilstoši, aktīvais = krāsaina mala uz `--surface2`, ne sarkans pildījums. Aiz 12. tēmas pogas nāk ar `hidden` un poga «Vēl N tēmas» (`data-topic-more-toggle`) tās atklāj; `ppv1.js::revealTopicButtons()` to dara arī pats, kad `?tema=` vai Pārskata čips mērķē uz sakļautu tēmu — aktīvā poga nekad nav neredzama. Slazds, ko noķēra ekrānuzņēmums pēc pirmā rendera: `hidden` atribūtu pārraksta pogas `display: inline-flex`, tāpēc CSS vajag skaidru `[hidden] { display: none }`. Renders: `src/render/politicians.py` `claim_topic_chips` (`claim_topics` alfabētiskais saraksts paliek esošajiem lasītājiem), `TOPIC_FILTER_VISIBLE = 12`. Testi `tests/test_profile_topic_deeplink.py` (+4, krita pirms). Otrs operatora jautājums — deep-link no tēmas lapas uz profilu ar Pozīciju cilni un tēmas filtru — jau strādāja kopš 2026-09-05 (6) T4 un ir live; nekas nebija jāmaina. Nav deployots — aiziet ar nākamo rutīnas pilno renderu.

## 2026-09-07 (10) — Verdiktu izpilde 2026-09-06 noslēgta: 52 rindas, deviņi Opus bloki, backlog attīrīts

Operatora lēmums 2026-09-06 («visiem kā rekomendēts, bet jaunā sesijā») izpildīts vienā sesijā ar deviņiem paralēliem Opus aģentiem pa grupām (A, B, C, D, rinda 30, E1–E4), katrs ar savu ziņojumu, orķestrators komitēja pa grupām (`999d20c8`, `1bf81d43`, `1eede1c4`, `5909f506`, `2d6485fc`, `1fbf37ee` + šis). Detaļas ierakstos (1)–(9) augstāk; per-rindas statuss `docs/verdikti-2026-09-06.md` galvā un pie katras rindas.

**Saucējs — 52 lēmumu rindas:** 31 izpildīta; 5 NESAKRĪT — mērījums apgāza verdikta pamatojumu, DB nemainīts (7 Mieriņa, 10 Rinkēviča citāts ir avotā ar citu pieturzīmi, 19 Svirskis — 2026-07-16 lēmums pretējs, 35 Žuravļevs — 28/28 pozīcijas no paša tvītiem, 37 NBS — `first_party` ar 40 pozīcijām); 1 nav izpildīta pretrunas dēļ (29 — 2026-09-05 (4) fakts Toro = Gobzems); 2 sagatavotas operatora apstiprinājumam (31 Zīle, 34 name_forms); 13 atliktas vai NĒ pēc paša ieteikuma. Rindas 53–57 izgrieztas. Ārpus verdiktiem, bet tajā pašā sesijā: divas stances ar nepareizo Meļņa priekšvārdu izlabotas (#20402, #20776) un 5 testu butaforijas rindas izņemtas no ražošanas `image_audit`.

**Kas gaida operatoru (pieraksts `BACKLOG.md` § Atliktais pēc 2026-09-06 verdiktiem):** `data/fix_grupaD_zile_negative_patterns_2026-09-07.sql`, `data/proposed_name_forms_2026-09-07.md`, `data/fix_grupaE_subject_demote_2026-09-07.sql` (3 027 vēsturiskas `subject` rindas), pirmais `python -m src.csp --apply`, citātu triāžas sesija (50) ar 7 jauniem 17. pārbaudes id, video (51). **Nekas nav deployots** — avota etiķete (41), Nozīmīguma vārdi (09-06) un divi jaunie profili (Pujāts, Freifalts) aiziet ar nākamo rutīnas pilno renderu + deploy. Verifikācija: `bash scripts/check.sh` → `all checks passed` (954 lapas, 2 538 testi) pirms grupas E commit; backlog `tests/test_backlog_index_sync.py` + `test_wiki_lint.py` 29 passed. Backlog: `BACKLOG.md` + `backlog/*.md` 1 024 → 865 rindas (191 → 168 KB), 11 ieraksti izgriezti, 13 pārrakstīti, 2 jauni, 0 svītrojumu.

## 2026-09-07 (9) — Avota etiķete no `source_domain`, viens attēlu budžeta saucējs, CSP ieejas punkts, X pūla pārmērījums

**Verdikti 41, 47b, 48, 49b.**

**41 — avota etiķete.** Claim virsmas etiķeti atvasināja no URL hosta, tāpēc 176 pozīcijas
lasītājam nesa izdevēju «pmo.ee» — Postimees Grupp saīsinātāju, ko neviens neatpazīst —,
lai gan `documents.source_domain` visām 2 125 šādām rindām jau glabāja pareizo `tvnet.lv`.
Jauna `_domain_label()` ņem etiķeti no `source_domain` un uz URL hostu atkāpjas tikai
rindām bez dokumenta (`saeima_vote`, `document_id` NULL). Pieslēgtas visas virsmas vienā
piegājienā: Pozīcijas plūsma, tēmu lapas (`topics.py:164`), «Uzmanības centrā» trīs citātu
vaicājumi, pretrunas visās piecās vietās (caur `_enrich_contradiction`) un dienas pārskata
skelets. URL NAV migrēts — tas ir `store_claim()` idempotences trijnieka daļa. Kontrolvaicājums
apstiprināja, ka `pmo.ee` ir vienīgā novirzes klase korpusā (`instr(source_url, source_domain)=0`
→ 2 125 rindas, visas tvnet.lv). Vārts: `tests/test_source_domain_label.py` (6 testi, pirms
labojuma visi seši krita). Šaurais renders (`--only=politiki,temas,pozicijas,pretrunas,dashboard`,
199 profila lapas) izvadē: `pozicijas-data.json` 176 → 0 `pmo.ee`, tēmu lapās 20 → 0. Publicētie
pārskati un ar roku rakstītās sintēzes NAV pārrakstītas.

**47b — viens attēlu budžeta saucējs.** `cli thread` un tiešie `generate_image()` izsaukumi
`brief_images` rindu neraksta nekad, tāpēc mēneša budžets (griesti 5,00 USD) mērīja tikai
`brief --note-id` ceļu; 2026-09-06 divi sintēzes attēli reģistrā nebija vispār. Jauna
`image_audit` tabula (`kind`, prompts, modelis, izmaksa, status), ko raksta pati
`generate_image()` — veiksmei 0,039 USD, galīgai kļūdai 0,0 USD, atkārtojumi vienā rindā.
`brief_images` paliek apstiprināšanas darbplūsma; jauna tabula, ne `note_id NULL`, jo tā
kolonna ir NOT NULL FK un tās maiņa SQLite-ā prasītu tabulas pārbūvi. Migrācija iekopēja
visas 311 vēsturiskās rindas (daļējs UNIQUE indekss to padara idempotentu), tāpēc
`monthly_cost_usd()` pārslēgšana summu nemainīja: 0,6240 USD pirms un pēc. Klāt
`cli thread --style light|sepia` — līdz šim sepia tika pievienots bez nosacījuma, tāpēc
gaišais variants CLI nebija sasniedzams un 2026-09-06 prompts palika vienreizējā skriptā.
Vārti: `tests/test_image_audit.py` (12 testi); mutācijas pārbaudē, noņemot audita ierakstu,
krīt 4 no tiem. Blakusseka, izlabota tajā pašā sesijā: pirmais `test_nanobanana.py` palaidiens
pēc migrācijas ielika 5 butaforijas rindas ražošanas bāzē (+0,078 USD) — dzēstas ar pāra
rollback, un `image_audit` pievienota conftest tripwire sarakstam.

**48 — X pūls pārmērīts.** `scripts/probe_x_cookies.py`: 5 sloti × 4 endpointi = 20 pārbaudes,
0 neveiksmju. `SearchTimeline` — tieši tas, kura dēļ pieminējumi krita atpakaļ uz `timeline` —
atbild visos piecos slotos (3. slots pēc viena transaction-key pārbūves). Pūls ir vesels
2026-09-07, ne tikai 2026-08-04. Lēmums par `search` pārplānošanu paliek operatoram.
Piezīme metodei: `get_pool().status()` šim nederētu — tas rāda tikai procesa iekšējo stāvokli
un svaigā procesā vienmēr ziņo 5/5 «available».

**49b — CSP ieejas punkts.** 2026-08-15 operatora lēmums PIESLĒGT `src/csp/` sync stāvēja
neizpildīts, jo `sync_all(conn)` nebija neviena izsaucēja. Jauns `python -m src.csp`:
noklusējums ir sauss palaidiens pret `data/csp.db` KOPIJU (kopija, ne tukša bāze — `upsert_rows`
ir INSERT OR REPLACE, tāpēc tikai pret esošajiem datiem delta ir patiesa), `--apply` jāraksta
ar roku, nulle atsvaidzinātu tabulu → exit 1. Pirmais sausais palaidiens dzīvē: 10/10 tabulu,
1 489 fetčotas rindas, `csp_data` 1 481 → 1 509 (+28) pret 2026-04-14 iesaldētajiem datiem;
izsekotais binārais fails palika neskarts. Vārts: `tests/test_csp_entrypoint.py` (6 testi,
tostarp «sausais palaidiens atstāj failu baitu-identisku»). Runbook: `wiki/operations/commands.md`
§ CSP statistikas datu atsvaidzināšana. Pirmais `--apply` apzināti nav izpildīts — tā ir
datu mutācija izsekotā binārā failā, kas aiziet publiskajā spogulī.

## 2026-09-07 (8) — Verdikti 24, 42, 44: divi jauni audita saucēji un `claims.review_status_at`

**24 — ne-kanoniskās tēmas kā vārts, ne koda labojums.** `src/db.py::store_claim` joprojām nenormalizē `topic`, un tas ir apzināti: `topic` ir daļa no idempotences atslēgas, un normalizācijas ieslēgšana bez sausā palaidiena ir tieši tā klase, kas 2026-08-02 saražoja 4 087 dublikātus. Vietā stāv `/audit-integrity` 18. pārbaude — `scripts/audit_topic_canonical.py` salīdzina katru distinkto `claim_type='position'` tēmu pret `src/topic_map.py` 33 kanoniskajām grupām. Bāzlīnija: `checked=6564 distinct=33/33 flagged=0`. `checked=0` ir izejas kods 2 ar tekstu «salauzti vārti», ne tīrs rezultāts.

**42 — 9. pārbaudes aklā zona ieguva saucēju.** Partijas↔frakcijas pārbaude grupē pēc `saeima_individual_votes.faction`, tāpēc politiķis bez neviena frakcijas etiķetēta balsojuma tajā neparādās vispār — ne kā atradums, ne kā pārbaudīta rinda, un klusēšana lasās kā «tīrs». Tā pid=224 R. Meļņa partija izdzīvoja divus mēnešus un 26 publicētus pārskatus. `scripts/audit_minister_vote_coverage.py` nosauc klasi ar skaitli un sarakstu: bāzlīnija `checked=25 flagged=6` — pid 15 Braže, 64 Vītols, 155 Melbārde, 158 Lāce, 159 Uzulnieks, 224 Melnis. Rinda sarakstā nav defekts; tā ir vārds, ko automātiskā verifikācija nesasniedz.

**44 — `claims.review_status_at`: 14 dienu vārti beidzot mēra pareizo faktu.** Jauna kolonna, ko uztur TIE PAŠI divi trigeri, kas `review_status`; vērtība ir LV laiks brīdī, kad atvasinātais statuss mainās (`datetime('now','+3 hours')` — tas pats formāts, ko raksta `now_lv()`). Stilistisks `reasoning` labojums zīmogu neatiestata, jo trigeris salīdzina veco statusu ar jauno. Backfill nav: vēsturiskajām rindām nav zināms marķēšanas brīdis, tāpēc tām ir NULL, un lasītāji lieto `COALESCE(review_status_at, created_at)` — vecākais zīmogs, t. i., skaļā puse. Vārta forma pārcelta no promptiem uz kodu (`src.db.open_review_queue()`, `REVIEW_QUEUE_AGE_DAYS`), un četri nesēji tagad to lasa: `@quality-reviewer` § A, `quality-bars.md`, `weekly-routine.md` § 5 un `/audit-integrity` 4. pārbaude. Iemesls: 2026-08-22 vārti ziņoja par 19 pārkāpuma rindām, kas visas bija ienākušas rindā iepriekšējā dienā — reāls darbs, nosaukts ar nepareizu pamatojumu, un tas būtu atkārtojies pie katras retro-marķēšanas. Migrācija idempotenta (`src/db_migrations.py` + `src/schema.sql`), pāra faili `data/{fix,rollback}_grupaE3_review_status_at_2026-09-07.sql`; rollback pārbaudīts uz svaigas DB, un tā atjaunotais trigeru teksts sakrīt ar to, kas bija `sqlite_master` pirms maiņas.

Testi (visi krita pirms labojuma): `tests/test_audit_topic_canonical.py` (6), `tests/test_audit_minister_vote_coverage.py` (7), `tests/test_review_status_column.py` (+8, kopā 21). Dzīvē: 662 280 claims, 0 rindu ar zīmogu, `needs_review=55` (≤7d 48, 8–14d 7, >14d 0).

## 2026-09-07 (7) — `role='subject'` prasa runātāju: releja mediju slots un biroja balss retvīti

Operatora verdikti 36 un 38 ieviesti kodā; 37 noraidīts ar mērījumu. Jauns modulis
`src/roles.py` ir vienīgais īpašnieks jautājumam, kurš drīkst nest `role='subject'`, un abi
bulk-rakstītāji — `db.insert_document` un `matcher.link_politicians_to_documents` — iet caur to.
Divas klases vairs nerada `subject` rindas: (a) releja mediju sloti (`relationship_type=
'organization'` UN `feed_type='relay'` konts — LETA un vēl 10), kuriem aģentūras kredītrinda
«aģentūrai LETA pastāstīja…» bija padarījusi LETA par 934 nepārskatītu web doku subjektu pie
0 pozīcijām mūžā; (b) kaili retvīti no biroja balss konta (@Brivibas36), kur tvīts glabājas
politiķa paša status-URL, tāpēc autora sakritība tam piešķīra `subject` — 34 rindas, pid=10 ×22.
Slotu kopa ir tas pats šaurais UN, kas kopš 2026-08-02 dzīvo `src/scope.py`; `relay_media_pids()`
ir tā Python dvīnis, lai rindas filtrs un junction rakstītājs nevarētu atšķirties.

Verdikts 37 (NBS pid=204 tajā pašā vārtā) NAV izpildīts: NBS ir `organization`, bet
`feed_type='first_party'` un tam ir 40 pozīciju claims, 22 no tām augustā (pēdējā 09-04) —
vārts pār `relationship_type='organization'` nogrieztu dzīvu kanālu, tāpat kā LDDK, LVM,
Valsts kontrolei un Latvijas Bankai. NBS piesārņojums ir 32 doki, no kuriem CVK programmu
doki ir 2; tas ir domēna, ne lomas jautājums.

Mērījumi pirms/pēc: nepārskatītie web doki 6 493 (nemainīgi); no tiem ar `subject` rindu
1 257, pēc sagatavotās vēsturiskās demotēšanas 295. Ekstraktora darbs nemainās (rindas
semantikā 225 → 225) — LETA no rindas jau bija izslēgta 2026-08-02; mainās metrikas nozīme un
tas, ka releja slots vairs nesaņem ~600 jaunas `subject` rindas mēnesī. Vēsturiskās 3 027
rindas gaida atsevišķu lēmumu: `data/fix_grupaE_subject_demote_2026-09-07.sql` +
rollback (pārbaudīti uz DB kopijas: 95 dzēstas, 2 932 demotētas, rollback atjauno baitu pa
baitam). Vārti: `tests/test_subject_role_guards.py` (4 no 6 krita pirms labojuma).

## 2026-09-07 (6) — Divi jauni sekotie slots un trīs mērīti «nē» matcher formu jautājumos

Verdiktu izpilde, D grupa (rindas 27, 28, 31, 34, 35; rinda 30 atsevišķi).

**Iesēdināti divi slots.** pid=246 **Guntis Pujāts** (Valsts robežsardzes priekšnieks,
ģenerālis; `party=NULL`, `relationship_type='neutral'` pēc Sārta/Slaidiņa konvencijas)
un pid=247 **Agris Freifalts** (partija «Gobzema saraksts», Vidzemes saraksta līderis;
partija verificēta pret CVK un LTV, ne pret kopējā saraksta formulējumu ziņās). Abiem
`name_forms` ar diakritikas un ASCII variantiem, ≤4 zīmju formu nav, X konts nav likts —
Pujātam kandidāts `@guntispujats` nav apstiprināms dzīvē (x.com atbild 402, korpusā
0 doku), Freifaltam publisks X konts nav atrasts. Junction pārsaiste 38 dokiem:
51 jauna rinda (26 pid=246, 9 pid=247, 16 blakus citiem). **Kohortas audits (T13)
atrada 2 nepatiesas rindas no 26** — doki 6820 un 26974 runā par kardinālu Jāni
Pujātu, ne par ģenerāli; abas dzēstas. Korpusā ir vēl divi vārdabrāļi (Edgars, Jānis
Pujāts), kurus priekšvārda veto noturēja pareizi. Apstiprināts arī, ka Freifalta vārdi
līdz šim gāja pid=234 Arigo Toro slotā (7 no 9 dokiem).

**Trīs mērījumi, kas apgāza verdikta pamatojumu.** (1) Tukšas `name_forms` NEnozīmē
trūkstošus locījumus — matcher tos ģenerē pats; trūkst tikai ASCII variantu, un tie
89 649 doku korpusā ir vērti **5 dokumentus** (61 no 66 ierosinātajām formām nedod
nevienu trāpījumu; lielie skaitļi — `Briskens` 180, `Krustpunkta` 190 — izrādījās X
handli, ko H ceļš jau ķer). (2) pid=187 Žuravļeva slots nav tukšs: RT tiešām ir 211 no
237 `subject` dokiem, bet **visas 28 pozīcijas nāk no viņa paša tvītiem**, un
`feed_type='relay'` tās nogrieztu — RT troksnis pieder 36.–38. rindas mehānismam.
(3) `negative_patterns` ir reģistrjutīgs substring, ne regex, tāpēc «vadītāj*» formā
tas nestrādātu.

**Sagatavots, bet neizpildīts** (`name_forms` un `negative_patterns` paliek operatora
robeža): Zīles amata frāzes veto pid=21 — 41 doks korpusā, 0 no tiem satur īstu Roberta
Zīles vārda formu, 2 nepatiesas junction rindas; eval vārti abās pusēs vienādi
(`B2D2H fp_links=1`, zelts 97,93 %). Faili `data/{fix,rollback}_grupaD_*_2026-09-07.sql`
un `data/proposed_name_forms_2026-09-07.md`.

---

## 2026-09-07 (5) — Vēstneša akti vairs nepazūd klusi; nogrieztais ievads tiek karogots, ne atmests

**Verdikts 39 — Vēstnesis.** `src/analyze.py` komentārs izslēgšanu attaisnoja ar
to, ka saturs sasniedz dienas pārskata sadaļu «Šodien izsludināts». Tā sadaļa
dzīvoja `generate_telegram_brief()` iekšpusē un tika izmesta 2026-08-03
(`60c878f4`) — publicētā pārskatā tās nav bijis nekad, tātad izslēgšanai
kompensējošas virsmas nebija vispār. `backlog/agenti-pipeline.md` apgalvojums,
ka filtrs ir spogulēts `src/scope.py`, arī nebija patiess: modulī tā vārda nav.
Abi komentāri pārrakstīti ar mērījumiem (2 149 doki 30.04.–04.09., no tiem ≈ 800
sludinājumu klases, 11 claims no visas platformas jebkad, 465 doku virsrakstā MK
/ Saeima / rīkojums / likums), un `src/scope.py` tagad skaidri pasaka, ka
dokumenta puses filtrs tam nepieder.

Kompensējošā virsma: `src/routine.py::vestnesis_acts_for()` + rinda
`print_routine()` — dienas Vēstneša doki, kuru virsraksts sākas ar «Ministru
kabineta» / «Saeimas» / «Valsts prezidenta», uzskaitīti orkestratoram ar id un
virsrakstu, saucējs «N no M Vēstneša dokiem dienā». Tā ir rinda, ne solis: solis
te būtu mūžīgi zaļš, un vārts, kas nevar krist, nav pierādījums. Dienas robeža ir
`DATE(scraped_at)`, tāpat kā 1. un 2. solim — piecu rītu logs pēc definīcijas
attiecas tikai uz `political_tensions` un `context_notes`. Vārts nostrādāja uz
dzīviem datiem tieši 2026-08-26 (doc 95670 «Ministru kabineta krīzes vadības
sēdes protokols» — septiņi valdības termiņi tās dienas galvenajā tēmā,
`reviewed_at IS NULL`). Tests: `tests/test_routine.py::TestVestnesisActsAreSurfaced`
(6, mutācijas pārbaudīts pa prefiksu tuple).

**Verdikts 40 — nogrieztais ievads.** Raksti, kuru pirmā rindkopa ingestā
neiekļaujas, sākas ar anaforisku vietniekvārdu («Viņš uzsvēra…»); klase auga 32
→ 56 divās nedēļās, bet trīs no tiem izvilktās pozīcijas pret pilnu tekstu deva
0 misatribūciju. Tāpēc vārts KAROGO, neatmet: `_looks_like_cut_lede()`
(`src/ingest_rules.py`, šaurs — divas formas, reģistrjutīgs), skaitītājs
`_ingest_source` cilpā, doc id `logs` rindas `details` (`cut_lede_doc_ids`) —
bez shēmas migrācijas — un saucējs ielādes žurnālā: «N no M web dokiem ar
nogrieztu ievadu», arī tad, kad N = 0. Predikāts palaists pār visiem 14 737 web
dokiem: 56 trāpījumi, precīzi sakrīt ar SQL bāzlīniju; 56 esošie doki apzināti
neaiztikti. Tests: `tests/test_ingest_cut_lede.py` (18, divas mutācijas
pārbaudes).

## 2026-09-07 (4) — Meļņu junction pāratribūcija; kailā «Melnis» klase pārmērīta

Verdikta rinda 30 izpildīta. Pārbaudīti visi 392 doki, kuriem pid=157 (Kaspars Melnis, ZZS)
ir `document_politicians` rindā, tostarp 25 verdikta mērītie («aizsardzības ministr» bez
«Kaspars Melnis») un 9 ar «Raiv*» — kopā 28 izlasīti pilnībā. Deviņi no tiem (32407, 32710,
32756, 32776, 32785, 33456, 34720, 34726, 34728) ir par Raivi Melni (pid=224), un to piesaiste
pid=157 bija kļūdaina: piecos gadījumos pid=224 jau bija piesaistīts, tāpēc kļūdainā rinda
dzēsta, četros rinda pārcelta uz pid=224 (loma visos `mentioned`). Deviņas rindas mainītas,
tieši tik, cik plānots; pāris `data/fix_melni_reattrib_2026-09-07.sql` +
`data/rollback_melni_reattrib_2026-09-07.sql`, atgriešana pārbaudīta sausajā skrējienā uz
shēmas kopijas (atgriež sākotnējās 57 rindas).

Verdikta bažas par pozīcijām neapstiprinājās: **neviena no 54 pid=157 pozīcijām nepieder
Raivim Melnim**. No deviņiem kļūdainajiem dokiem nenāk neviena pozīcija (visi ar lomu
`mentioned`), 37 no 54 ir Kaspara paša X konta ieraksti, pārējās 17 — raksti par klimata un
enerģētikas ministru vai Publisko izdevumu un revīzijas komisijas priekšsēdētāju. Tāpēc ne
kolīzijas vaicājums pret `(224, source_url, topic)`, ne `reembed_claims.py` nebija vajadzīgs.

Atradums, ko verdikts neparedzēja: divās pozīcijās (#20402 Liepnieks 11.05., #20776
Stendzenieks 23.05.) mūsu pašu `stance` tekstā kailā avota forma «Melni» ir izvērsta uz
nepareizo priekšvārdu — «Kaspara Meļņa» Raivja vietā; avota tvītos priekšvārda nav, tātad to
pievienoja ekstrakcija. Abas aizgāja publicētos pārskatos (piezīmes #223 un #225, pēdējā trīs
vietās). Pārskati netiek pārrakstīti; DB rindas izlabotas orkestratora kontekstā —
`data/fix_melni_stance_vards_2026-09-07.sql` ar pāra rollback, `reembed_claims.py 20402 20776`
→ abi vektori MAINĪJĀS (`quote` verbatim, neaiztikts).

Matcher eval bāzlīnija pēc labojuma (`scripts/eval_matcher_collisions.py`, pilns skrējiens):
B2D2H konfigurācijā `fp_links_residual` = 1, `gold_hit` = 1796 — abi vārti (FP ≤ 3, zelts
≥ 1260) izturēti. Vienlaikus konstatēts, ka 32 marķēto FP gadījumu kopā Meļņa klases NAV,
tāpēc šie vārti to nevar noķert; pirms jebkuras `negative_patterns` maiņas kailajai formai
eval-ā jāieliek Meļņa gadījums. `negative_patterns` nav mainīti.

## 2026-09-07 (3) — Trīs konvencijas nesējos + confidence-drift saucējs (verdikti 20, 23, 25, 26)

**`stated_at` ārpus 7 dienu loga (20).** `@claim-extractor` Step 4 tagad nes rakstītu noteikumu: ja
izteikuma faktiskā diena ir ārpus dienas pārskata 7 dienu grīdas (`src/briefs.py::_BRIEF_DAY_CLAIM_SQL`),
`stated_at` ir publiskošanas diena, bet izteikuma īstais datums jāpasaka `stance` tekstā; 7 dienu logā
nekas nemainās, un vēsturiskās rindas netiek bīdītas (08-25 arguments). Ceturtā šīs klases instance —
#704179 (Dombrovska 30.07. datētā vēstule, publiskota 27.08.), kas DB jau ir konvencijas paraugs; agrākās
#703962, #703963, #703974. `wiki/operations/agenti/claim-extractor.md` Step 4 nespoguļo (0 trāpījumu uz
`stated_at`), tāpēc sinhronizācija nebija vajadzīga.

**Māsas balsojumu kopsavilkums (23).** Pēdējais neizpildītais 08-17/08-18 Saeimas verdikta gabals
(variants b) pierakstīts divās vietās: `generate_claims_from_votes` docstring un `@saeima-tracker` 3.B
(vēsturiski Step 3.5). `summary` pieder likumprojektam, ne balsojumam, tāpēc viena `document_nr` māsas
balsojumi mantoja cita balsojuma iznākuma teikumu stancē (6916 nes 6103 iznākumu 84 claims; 246
balsojumi, ~20k claims). Vēsturiskās rindas netiek pārrakstītas — frāze lasāma kā likumprojekta
konteksts; jauniem ne-lasījumu balsojumiem kopsavilkumā iznākuma teikums ir aizliegts. Koda loģika
nemainīta.

**Laika apgalvojumi (25).** `@quality-reviewer` § C2 (kopš 08-25) papildināts ar kontrolsaraksta rindu —
katrs laika apgalvojums spriedzē vai tendences piezīmē pārbaudāms pret avota datumiem tikpat stingri kā
citāts pret avota tekstu — un `TIME_PHRASES` sarakstu (8 → 11 frāzes: «nedēļas laikā», «pēc nedēļas»,
«dažu dienu laikā»). Verdikta premisa, ka rindas nav vispār, neizturēja: sadaļa eksistēja, trūka tvēruma.

**Confidence drift ar saucēju (26).** `check_confidence_drift()` klusē, kad kādā pusē ir mazāk par 5
claims (`_MIN_HALF_CLAIMS`, agrāk 3), un katra brīdinājuma rinda — gan atskaitē, gan rutīnas statusā —
tagad iet caur `format_drift_line()`, kas rāda n abās pusēs. 08-24 «Degviela un enerģētika +0,23»
brīdinājums bija divi n≤3 paraugi; brīdinājums bez saucēja ir vārti, kas nevar nokrist. Testi:
`tests/test_confidence_drift.py` (12 passed), t.sk. n=4 klusēšana, n=5 robeža un vārts, kas prasa, lai
rutīna lieto to pašu formatētāju. Krišana pirms labojuma pierādīta ar palaidienu (n=4 izlase deva
brīdinājumu).

## 2026-09-07 (2) — Verdiktu izpilde, grupa B: `role` / `relationship_type` T6 klase

Četras `tracked_politicians` rindas izlabotas, katra ar savu `data/{fix,rollback}_grupaB_pid<N>_*_2026-09-07.sql` pāri (uzrakstīts un `EXPLAIN`-kompilēts pirms izpildes; katrs UPDATE mainīja tieši 1 rindu, kā plānots).

- **pid=155 Melbārde `role`** → «Ārlietu ministrijas parlamentārā sekretāre» (bija «Izglītības un zinātnes ministre (demisionējusi)»). Pieci DB doki (69331 tvnet 07-16 ar iecelšanas naratīvu; 94265, 94382, 94392, 94395 08-25) plus mfa.gov.lv oficiālās ziņu lapas (pārbaudītas 09-06). **`party` apzināti NEmainīta** — JV nosauc viens avots, `saeima_individual_votes` pid=155 = 0 rindu, tāpēc T6 frakcijas krustpārbaudes nav.
- **pid=209 Štekerhofs `relationship_type`** `inactive` → `tracked`. Mērījums apstiprina verdikta skaitli: pēdējā gadā `faction='ZZS'` **514**, `NULL` 81 (kopā 595), pēdējais balsojums 2026-09-03; visu laiku 3 662. Sekas pārbaudītas dzīvē, ne pieņemtas: `get_pending_politicians(days=30)` tagad atgriež pid=209 (`doc_count=2`), tātad **doc 90283** (airBaltic, `subject`, `reviewed_at IS NULL`) ir atgriezies rindā kopā ar divām neizvilktām Kulberga (pid=10) un Rokpeļņa (pid=126) pozīcijām. **Precizējums pret `backlog/dati-db.md` § 2026-08-25 (a):** doc **89625 NEatgriežas** — tā `subject` ir pid=211 Rosļikovs, kurš paliek `inactive`.
- **pid=212 Labanovskis `role`** → «Smiltenes novada domes priekšsēdētājs» (bija «Saeimas deputāts (14. Saeima)»; pēdējais balsojums 2025-02-20, pēdējā gadā 0). Patiesības avots — smiltenesnovads.lv § Domes vadība. `relationship_type='inactive'` apzināti NEmainīts.
- **pid=33 Ruģēns `role`** → `NULL` (bija «Jaunietis no franču vēstniecības», sēšanas artefakts, kas renderējās publiskajā profilā). pid=39 Aizupietis `role IS NULL` apstiprināts kā apzināta vērtība.

**Bez DB izmaiņām, ar mērījumu.** *pid=168 Kronbergs:* izlasīti 10 no 27 `subject` dokiem (2026-02..08, astoņi avoti) — **10 no 10 ir par DB Kronbergu, nulle identitātes sajaukšanas**. 73:1 attiecību izskaidro divi fakti, ne homonīms: 26 no 27 `subject` dokiem jau ir `reviewed_at NOT NULL` (ekstrakcija atgrieza 0 pozīciju), un korpusā ir tikai viens pirmās personas avots — doc 37626, viņa paša atklātā vēstule, no kuras abas pozīcijas (#20562 `Valsts pārvalde`, #20563 `Korupcija un KNAB`) arī nāk; abu atribūcija un citāti verificēti pret avotu. DB `role='Bijušais Valsts kancelejas direktors'` ir pareizs — doc 91753 «bijušais ZM valsts sekretārs» ir agrāks amats (apstiprina doc 33408), ne pretruna. *pid=62 Svirskis:* `social_accounts` rinda `realNepareizais` **NAV deaktivēta** — 2026-07-16 operatora lēmums (CHANGELOG-arhivs) jau atzina abas rindas par leģitīmām; `/audit-integrity` 2. pārbaudes (c) zars nefiltrē pēc `active`, tāpēc `active=0` karogu nemaz nenoņemtu; un `src/social.py` fetch filtrē `active = TRUE`, tātad tas apturētu dzīvu kanālu (1 689 doki 04-01..09-05, satura pārklāšanās ar @ESvirskis pēc `content_hash` = 0). Ieteiktā slēgšana — dokumentēts izņēmums bāzlīnijā, kā pid=27 Bordāns. *Atlikti:* pid=181 Bartaševičs (gaida Rēzeknes pašvaldības/CVK avotu; 0 balsojumu; blakus — `name_forms` ir tukšs) un pid=211 Rosļikovs (0 balsojumu kopš 2025-06-05, doc 89625 liecina par apcietinājumu).

## 2026-09-07 (1) — Verdiktu izpilde: A grupas per-rindas dati + divas C grupas DB rindas

Izpildītas 2026-09-06 verdiktu sarakstā rindas 1, 3, 8, 9, 21 un 22; rindas 7 un 10 pēc avota
izlasīšanas atzītas par NESAKRĪT un DB nemainīts; rindas 2, 4, 5, 6 pārbaudītas kā «nedarīt».

**Atsauktas četras pozīcijas** (pāris `data/fix_grupaA_atsaukumi_2026-09-07.sql` /
`data/rollback_grupaA_atsaukumi_2026-09-07.sql`): #689743 un #689646 (Sprūds, pid=16, «Droni») kā
ceturtā un trešā rinda vienā četru dienu klasterī — pirmavots #689540 un tā paplašinājums #689609
palikuši; #703870 (Braže, pid=15) kā pašas RT par savu 08-20 tvītu (#690485 palicis); #704024
(Dombrovskis, pid=229) kā gadadienas apsveikums bez jauna instrumenta pēc 08-25 robežas. Pirms
dzēšanas mērīts: 0 `contradictions` atsauču (saucējs 29), pa 1 vektoram katrai (saucējs 664 757),
0 pieminējumu `context_notes`/`political_tensions`. Avota doki 87126, 89013, 91859, 93731 palikuši
ar `reviewed_at` — trīs tvīti turpina rādīties politiķu profilu X cilnē; atsaukta ir atmina.lv
apgalvojuma, ne cilvēka ieraksta klātbūtne. Visas četras bija citētas jau publicētos dienas
pārskatos (piezīmes #461, #467, #485, #496) — pārskati netiek pārrakstīti.

**Divas tēmas salāgotas ar māsas pozīcijām:** #704121 «Digitālā politika» → «Korupcija un KNAB»
(viena nostāja ar #690491) un #704165 «Ārpolitika» → «Aizsardzība un drošība» (tas pats 5 %-no-IKP
instruments, ko nes #547937 un #17860). Idempotences kolīzijas SELECT abām pirms izpildes: 0 rindu
uz mērķa trijnieka.

**#521109 (Krusts) stance paplašināta** no 229 uz 339 zīmēm ar avota centrālo vērtību tēzi (politikas
saturs, kas ģimenes dzīvi neizvirza par vērtību) un līdzekļu avotu; šaura stance bija tā, kas ražoja
viltus pretrunas kandidātu #521109 × #615877. `quote` verbatim, neaiztikts.

Visām trim mainītajām rindām pārrēķināts vektors (`reembed_claims.py 704121 704165 521109` — trīs
reizes «MAINĪJĀS», apstiprināts arī ar SHA-256 pirms/pēc); `claim_vectors` 664 757 → 664 753.

**Divi verdikti atsaukti pēc avota izlasīšanas.** #703953 (Mieriņa): doc 91765 katru stances daļu
piedēvē viņai («Vienlaikus viņa uzsvēra…» seko tieši aiz «Mieriņa norādīja»), tāpēc nav ko sašaurināt —
premjera daļa stancē nav pārnesta. 615955 (Rinkēvičs): citāts doc 80022 **ir** — 251 no 252 zīmēm
sakrīt zīme zīmē pozīcijā 1327, atšķiras vienīgi noslēguma pieturzīme (claim `.`, avotā `,`, jo
teikums turpinās). 09-06 `instr()` = 0 bija pilnas virknes meklējums kopā ar punktu, tātad tā ir
pieturzīmju klase (verdikta 50. rinda), ne pārskrāpēšanas zudums; `quote` saglabāts un plānotais
`reasoning` papildinājums NAV rakstīts, jo tas ierakstītu korpusā nepatiesu apgalvojumu.

## 2026-09-05 (8) — «Koalīcija vs Opozīcija» tabulai pastāvīga paskaidrojoša rinda (skelets + renderis)

r/atminaLV lasītājs pie 09-01 pārskata jautāja, kā tiek lemts, kas ir «Opozīcija» un kas «Bez Saeimas frakcijas» — intuitīvi «visi ārpus koalīcijas = opozīcija», bet bloks nāk no `parties.coalition_status` (Data Contract #10), un tabula to nekur nepasaka. `src.briefs.BLOC_TABLE_EXPLAINER` (45 vārdi, lint 0) tagad iet tieši zem tabulas trijos nesējos: dienas skelets, nedēļas skelets un `_brief_markdown_to_html` render-laikā caur idempotento `add_bloc_table_explainer()` — tāpēc arī 171 glabātais pārskats to iegūst bez DB maiņas (tas pats princips kā `format_context_note`, 09-05 (6)). Stils `.bloc-explainer` `blog-post.html.j2` (`--text-muted`, 0,85 rem). `brief-writer.md` SAGLABĀ saraksts papildināts. Vārti: `tests/test_briefs.py::TestBlocTableExplainer` (4 — skelets ×2, render-injekcija + idempotence, bez tabulas nekas); `test_render_chars` bāzlīnijas (blog, analizes) pārģenerētas ar `REGEN=1`, jo templotes CSS maina baitus. Renders `--only=blog`, deploy `--no-delete`, live pārbaudīts 2026-09-05 + 2026-08-01.

## 2026-09-05 (7) — 09-05 rutīna publicēta: otrs ingest, 6 vakara pozīcijas, pārskats #542 ar attēlu 313

Otrs ingest 5/5 (30 web + 88 tvīti + 160 pieminējumi kopš 20:40) — **slazds:** `morning_ingest.py --help` nesaprot argumentus, bet `fetch_all_twitter` iekšējais argparse `--help` noķer un izmet `SystemExit(0)`, ko `step()` neķer (`Exception` vien) → ķēde klusi beidzas pēc RSS ar izejas kodu 0 un bez kopsavilkuma rindas; 2.–5. solis palaisti atsevišķi ar to pašu `morning_ingest` logs rindu (`note` laukā skaidrojums). Ekstrakcija: 4 Opus `@claim-extractor` aģenti, 19 politiķi / 29 doki → **6 pozīcijas #709077–#709082** (2 `needs_review`), `failures=[]` visos, 3 Mieriņas dublikāti (viens paziņojums trijos avotos) noķerti ±5 d pārbaudē, rinda 0 (paliek tikai relay/inactive sloti: LETA 12, Svirskis 2, Lūsis 1). Junction-atgūšana: `find_inversions(days=2)` 86 doki / 4 pāri, visi jau `extracted_at`. Pretrunas: 6 pārbaudītas, 0 atrastas, 7 noraidīti kandidāti logā (#655000). Spriedzes #265 (Ašeradens→Dombrava, imigrācijas laiks) un #266 (Velps→Kulbergs, 25 % likme); tendences #538–#541 (Budžets, Imigrācija, airBaltic, Aizsardzība; 118/107/83/95 vārdi). Pārskats #542 (`@brief-writer`, 17,4 KB, lint 0/6 likumi, 78 % segums) — orķestratora korektūra laboja 5 vietas (breadth «jāatliek»→«produktīvāk diskutēt», ZZS-klusē pretruna ar kastīti, `Skaitlis`→`-`). `@quality-reviewer` (ROUTINE_DAY 09-05): D1 «#709070 tēma pret reasoning» NAV defekts — tā ir tās pašas dienas operatora lēmums (CHANGELOG (5), rollback_flags), reasoning teksts ir novecojis; izpildīti D2 (ASL nav «opozīcija» — `not_in_saeima`, tekstā «ārpus Saeimas»), D3 (dienas vadošajam apgalvojumam pievienota `pmo.ee/8540463` saite), D4 (#709080 stance «jāpilnveido» — la.lv virsraksta verbs — → «būtu nepieciešams pārskatīt» pēc raksta, rollback `data/rollback_stance_709080_2026-09-05.sql`, re-embed MAINĪJĀS, labots 4 vietās: claims/tension #265/note #539/pārskats+wiki). D6 (marķieris `NEEDS_REVIEW:` #709077 nav prefiksā, 5/55 rindas tāpat) — atvērts, kosmētisks. Attēls: `@graphics-designer` pareizi ignorēja orķestratora «Economist ar virsrakstu» norādi par labu stāvošajam sepia/bez-teksta noteikumam; 2 kandidāti (312/313), operators apstiprināja 313. `check.sh`: ruff + 2440 testi zaļi, vienīgais kritiens `check_output` «sitemap bez blog/2026-09-05» — smoke renders bez `static`, narrow renders ar `static` slēdz. Deploy `--no-delete` pēc `approve_publish 2026-09-05`; live: pārskats 200, 4/4 attēla varianti 200, sākumlapa saista pārskatu. **Skill-piezīme:** `/dienas-rutina` variantu vārts (a) globo `output/atmina/images/briefs/*.png`, bet pamata PNG tur netiek kopēts (arī 09-04 nav) — saucējs 0 ir vārtu kļūda, ne trūkstošs attēls; pārbaude jāsien pie `-hero/-og/-card/-thumb` failiem vai pie `output/images/briefs/`. Neskarts: `docs/social/2026-09-05-*` un `docs/tweet_bank/2026-09-05-*` (09-04 pārskata sociālie melnraksti, radīti 20:55 citā procesā).

## 2026-09-05 (6) — Produkta/UX plāna T1–T4 ieviesti zarā `ux-2026-09-05` (nav deploy)

Plāns `docs/plans/2026-09-05-produkta-ux-to-do.md`; četri Opus implementētāji secīgi, katrs diffs pārskatīts orķestratora kontekstā, katrs commit ar pilnu `check.sh` (pēdējais: 2432 passed, `==> all checks passed`). **T4** `60665b11` — Pārskata tēmas čips ved uz `politiki/<slug>.html?tema=<tēma>#pozicijas`, `ppv1.js` validē tēmu pret filtra pogām (nezināma → «Visas»), sinhronizē parametru, «Kopēt saiti» pārnes cilni + filtru (`data-copy-state`); vārti `tests/test_profile_topic_deeplink.py`. **T2** `7c45b0a3` + `91512a16` — trīs sākumpunkti zem meklētāja (temas/personas/partijas), hero etiķete «No politiskās atmiņas» (kompozīta H2 paliek «Uzmanības centrā» — divas dažādas lietas, katrai viens nosaukums), atruna pie «Visvairāk pretrunu»; vēlēšanu skaitītāja dublējošā saite noņemta; `tests/test_index_entry_points.py`. **T1** `81eb8b43` — hero pretrunas kartīte rāda pilnu `summary` + `context_note` pirms citātiem (datu ceļš jau bija — tikai templote), karuseļa auto-pārslēgšanās noņemta, neaktīvās kartītes `display:none`; `tests/test_hero_contradiction_context.py`. **T3** `86ddb9ef` — profila cilnes: dabiskais platums + ritināma josla mobilajā, ≥44 px pieskāriena zona, roving tabindex + bultas/Home/End, hash-ielāde ieritina tikai joslu; hero punkti 44×44; `tests/test_profile_tabs_keyboard.py`. Orķestratora pārlūka pārbaude: sākumlapa 390/1280 px, profils 390 px `#saeima` — bez nogrieztiem tekstiem. **Nav darīts:** deploy, T5 lietojamības pārbaude (dalībnieki — operators), `backlog/vietne-ui.md` (b) tap-target ieraksts daļēji slēgts, bet nav rediģēts. Papildus tajā pašā sesijā: hero kopsavilkums `max-width: 72ch` (`389ca91e`); **dienas pārskata konteksta kastīte** — piezīme DB ir `- ` saraksts, bet skelets to ielīmēja bez tukšām rindām, un Markdown sarakstu izplūdināja vienā rindkopā (noslēguma teikums ielipa pēdējā punktā, «21. augusta …» rindkopa kļuva par `<ol>`). `src.briefs.format_context_note()` liek tukšas rindas ap sarakstu, aizsargā rindkopas sākuma kārtas skaitli un «Tendence (datums, virsraksts):» prefiksu pārvērš treknraksta virsrakstā ar datumu; izsauc gan skelets, gan `_brief_markdown_to_html` render-laikā (tāpēc arī glabātie pārskati sakārtojas — 91 no 171 ar kastēm, 50 ar prefiksu, 9 ar sarakstu; idempotents). Vārti `tests/test_brief_context_note_layout.py` (8), pārbaudīts renderētajā 2026-09-04 pārskatā. Atvērts: kartītes augstums telefonā ar 1200+ zīmju kopsavilkumu.

## 2026-09-05 (5) — Rutīnas 1.–3. solis + četri karogu lēmumi ar pāra rollback

Rutīna: ingest 5/5 (448 doki), 10 Opus `@claim-extractor` aģenti pa politiķiem, 34 sloti / 77 doki → **11 pozīcijas** (#709066–#709076), `failures=[]` visos izsaukumos, rinda 0; junction-atgūšana 79 doki / 4 pāri, visi jau apstrādāti; pretrunas 11 pārbaudītas, 0, 3 noraidīti kandidāti `logs.rejected_candidates`. Vakara soļi (2. ingest, spriedzes, tendences, pārskats) — nākamajā sesijā; pilns pieraksts `docs/HANDOFF-2026-09-05.md`.

Datu mutācijas pēc operatora lēmumiem (`data/rollback_flags_2026-09-05.sql`): **#709070** `Valsts pārvalde` → `Imigrācija` (viena ass ar #20524; sadursme 0, `reembed_claims.py` MAINĪJĀS); **Šnore (pid 7) `role`** → «Saeimas deputāts, Iekšlietu ministrijas parlamentārais sekretārs» (iem.gov.lv struktūrvienības lapa, T6 klase — DB kavējās vismaz kopš #704333 08-31); **#709043, #709075** marķieris → `Izvērtēts`, trigeris → `reviewed`. Apzināti atstāts: #709073 tēma, #709072 (paturēt, NE pārskatā), doc 101717 Hormuza lēmums (valdība 09-08).

## 2026-09-05 (4) — Pieci operatora lēmumi izpildīti: Ceriņš paliek, divi ekstrakcijas precedenti promptā, Toro = Gobzems, trīs vārtu labojumi, sweep plāns

Operatora atbildes uz 09-05 backlog ieteikumiem; katrs punkts ar pēdu.

- **#704196 (Ceriņš) — paliek un drīkst būt publiska.** Pirms lēmuma izmērīts, ka 08-27 renderu aizliegums jau bija pārkāpts: 09-04 vakara pilnais renders + deploy aiznesa profila lapu live (`last-modified` 2026-09-04 21:20 UTC, gan pozīcija, gan tvīts X apakšcilnē). Operators: atstāt. DB rinda neaiztikta (`needs_review` paliek — nav satura lēmuma). BACKLOG rinda slēgta, handoff STOP atcelts.
- **Divi 2026-09-03 precedenti → `claim-extractor.md` Step 3c.** (a) Ekonomikas datu izteikums bez rīcības priekšlikuma IR pozīcija; (b) iestādes slotā vērtējums IR pozīcija, operatīvs darbības paziņojums NAV. Dati: #709003 un #709015 marķieris → `Izvērtēts 2026-09-05:` (trigeris pārklasificēja uz `reviewed`, verificēts); **#706158 dzēsts** (LVM munīcijas sanācija — darbības paziņojums) kopā ar vektoru; doc 99549 paliek (feed item). Rollback `data/rollback_precedent_claims_2026-09-05.sql` (re-insert + norāde uz `reembed_claims.py 706158`). Pretrunu atsauces 0, pārskatu atsauces 0 (pārbaudīts pirms dzēšanas).
- **Toro (pid 234) IR pārdēvētais Aldis Gobzems** — operatora fakts, lasījums B; `wiki/persons/arigo-toro.md` to jau teica kopš seedēšanas, un 08-27 `matcher.md` ieraksts (lasījums A) bija nepareizs. `name_forms` PALIEK; `negative_patterns` += `"Gobzema sarakst"` (rollback `data/rollback_toro_negative_pattern_2026-09-05.sql`). Saucējs: 97 slota dokos 51 nes saraksta nosaukumu, **45 TIKAI to** (SKDS reitingi, partiju tabulas) — tie vairs nelinkojas; **6 doki ar īstu Toro pieminējumu + saraksta nosaukumu tagad arī ATKRĪT** (veto ir visa teksta līmenī — `src/matcher.py` `any(p in text …)`), apzināta cena. Vārti: `eval_matcher_collisions.py` B2D2H `fp_links=1` (≤3), `gold_hit=1791` (≥1260). **Blakus atradums, neatrisināts:** `match_politician("Aldis Gobzems paziņoja")` → `None` — priekšvārda veto (`Aldis` ≠ `Arigo`) nobloķē paša vēsturisko pilno vārdu; vēsturiskajiem 2022–2025 dokiem tas nozīmē klusu recall zudumu. Nav labots (matcher koda darbs ar eval vārtiem); pierakstīts `wiki/operations/seeding.md` § Vārda maiņa — jāatver kā backlog ieraksts tikai tad, ja parādās reāla ekspozīcija.
- **Trīs vārtu labojumi, katrs ar testu, kas krita pirms labojuma** (mutācijas tests: `git stash` uz `src/routine.py` → 3 no 3 jaunie testi krīt): (1) rutīnas 9. solis salīdzina ar `routine_day_window()` (05:00 LV), ne kalendāro dienu — pusnakts sync vairs nedod viltus ◐, un pēc pusnakts glabāta pozīcija joprojām pieder dienai (`tests/test_routine.py::TestWikiSyncStepUsesTheRoutineDay`); (2) `lint_wiki()` `stats` nes `pages_scanned` + `pages_by_dir` (`tests/test_wiki_lint.py::test_lint_reports_how_many_pages_it_scanned`); (3) `TEXT_FREE_CONSTRAINTS` nosauc autorības zīmes vārdā — paraksts, autogrāfs, monogramma, iniciāļi, kredītrinda (`tests/test_graphics_prompt.py::test_text_free_constraints_forbid_authorship_marks`); (b) pēcapstrādes vārts paliek atvērts.
- **Sweep plāns** `docs/plans/2026-09-05-vesturiska-ekstrakcijas-sweep-plans.md`. Galvenais mērījums: no 6444 nepārskatītiem web dokiem **5195 nav neviena politiķa junction rindas** (nav ko ekstraktēt), **925 ir LETA relay slots**, un īstā `tracked` politiķu rinda ir **~143 doki 60 slotos** + 84 `first_party` iestāžu doki. ~20 Opus aģentu A/B viļņos pa politiķiem, 2–3 relay empty-stamping aģenti. `wiki/index.md` «Nepārskatīts backlog: 222» mēra citu filtru nekā 6444 — abi skaitļi pareizi, nosauc, kuru mēra.
- Publiskais spogulis sinhronizēts tajā pašā sesijā (`05402cd`, 1466 faili, CI zaļš) — pieraksts `docs/funding/repo-sync.md`.

## 2026-09-05 (3) — BACKLOG higiēna: 4 slēgti ieraksti ārā, 9 dublikātu pāri apvienoti, indekss pārbūvēts, tagu vārti

Izpildīta `docs/plans/2026-09-05-strukturas-tirisanas-plans.md` 2. fāze; pierādījumi katram punktam — `docs/audits/2026-09-05-struktura-backlog-plani.md` §1–§6. **Saucējs: 86 ieraksti pirms, 79 pēc** (8 failos).

- **Četri ieraksti bija slēgti kodā, bet stāvēja kā atvērts darbs.** (1) `_strip_protected_regions` kastītes aizsardzība — slēgta `d82f98b8` (+`2cfc9760`), `protect_context_box` `src/lv_style.py:202-263` skaita ligzdotos `<div>` pēc dziļuma, regresijas tests `tests/test_lv_style.py:278 test_multiline_context_box_still_protected_after_fix` ir tieši par skeleta formu; rinda izņemta no `backlog/repo-higiena.md`. (2) Pretrunu kandidātu panelis — sk. (1) ierakstu šodien; BACKLOG rindā palicis tikai atlikums (`contradiction_candidates` tabula, `[DEFERRED]`). (3) `brief_images` (b) — `width` 1408 pret faktiskajiem 1376 SLĒGTS: `src/graphics/cli.py:166-167` atvasina izmērus no baitiem un nosauc atšķirību komentārā; tā kā (a) bija dublikāts, viss ieraksts izņemts no `vietne-ui.md`. (4) Render self-join kodols — slēgts jau 2026-08-20 (numpy precompute `vote_alignment_data`, ~101 s → ~2 s, orākuls `tests/test_vote_alignment_precompute.py`), tāpēc ieraksts pārsaukts par to, kas tiešām atvērts: lazy pre-fetch.
- **Deviņi dublikātu pāri → viens mājoklis katram.** pmo.ee avota etiķete (`avoti.md` → `vietne-ui.md`, saucējs pārmērīts 2 106 doki / 174 claims); `.png` ar JPEG baitiem (`vietne-ui.md` → `repo-higiena.md`, 281 no 284); divi `find_inversions` ieraksti → viens ar (a)/(b)/(c); trīs `subject`-lomas ieraksti → viens `[OPERATOR]` „lomai vajag runātāja pierādījumu" (LETA saucējs 242 → **979**); NBS pid=204 abas apakšklases → `matcher.md`; nepārskatīto doku uzkrājumi → `avoti.md`; `review_status` trigeris → `dati-db.md`; vec0 bāreņi (`claim_vectors` 7 010 + `document_vectors` 450) → viens `[DEFERRED]`.
- **Toro/Gobzems NAV izšķirts, un tieši tā tas tagad ir pierakstīts.** `matcher.md` teica, ka `Gobzem*` formas ir svešas personas paradigma; `avoti.md` teica, ka tās ir leģitīmas, jo Toro esot pārdēvētais Aldis Gobzems. Divi faili, divas pretējas mutācijas. Apvienotais ieraksts ir `[OPERATOR]` un nosauc ABUS lasījumus + faktu, kas jāpārbauda pret ārēju avotu (CVK/UR), ne pret rakstu. `name_forms` neaiztikts. Junction rindas pārmērītas: 88 → **97**, `position` claims joprojām 0.
- **Indekss pārbūvēts no tēmu failiem, un rinda tagad ir `### ` virsraksts VERBATIM.** Divi statusa driftu gadījumi (`[DEFERRED]` pret `[SLĒGTS 2026-08-20]`; nomests datums `[IZPILDĪTS 2026-09-04]`) un trīs pārrakstīti nosaukumi izzūd pēc konstrukcijas.
- **Vārti, kas iepriekšējo driftu nevarēja redzēt, paplašināti.** `tests/test_backlog_index_sync.py` salīdzināja tikai `### ` SKAITU — abi drifti gāja tam cauri zaļi. Jauns `test_index_status_tags_match_topic_file` salīdzina statusa tagu pa ierakstam, ar saucēju izvadā (0 aizzīmju indeksa blokā = salauzts parseris, ne tīrs rezultāts). **Mutācijas-pārbaudīts:** ar vienu pārrakstītu tagu indeksā (`[DEFERRED]` → `[OPEN]` balsojumi.html Step 3) tests krīt uz `vietne-ui` ar abu sarakstu diffu; pēc atjaunošanas 17 passed.
- **Astoņi plāni arhivēti** `docs/plans/archive/` ar divrindu izpildes galveni; `refactor-plan-2026-04-29.md` vienīgā atvērtā rinda (F5 migrāciju formāts) pirms tam pārcelta uz `backlog/vietne-ui.md` kā pilnvērtīgs ieraksts. `2026-08-14-repo-tirisanas-plans.md` 39 neatzīmētie čekboksi pārsvītroti, lai tie vairs nelasītos kā izpildāmas instrukcijas (viens no tiem ir bulk `mv` pār DB backupiem).

## 2026-09-05 (2) — `review_status` trigeris GLOB, ne LIKE: proza «izvērtēts» un kolonnas vārds `reviewed_at` vairs neatrisina rindas

Commits `f6ed9a5d`. `CLAUDE.md` § Escalation 2 apgalvoja, ka mazo burtu proza rindu nekad neatrisina; mērījums to atspēkoja abos virzienos — **3 no 700** `reviewed` rindām bija atrisinātas nejauši.

- `src/db.py::_REVIEW_STATUS_EXPR`: `LIKE` → `GLOB` (reģistrjutīgs katram burtam). Dzīvajā DB 3 rindas pārklasificētas `reviewed` → NULL (**#17964, #20846, #709064** — pēdējā `reasoning` tekstā bija kolonnas nosaukums `reviewed_at`); pāra rollback `data/rollback_review_status_glob_2026-09-05.sql`; shēmas bāzlīnija pārģenerēta.
- 2 jauni testi `tests/test_review_status_column.py` (prozas «izvērtēts» un kolonnas vārds `reviewed_at`) — **abi krita pirms labojuma**.
- Vienā piegājienā laboti arī faktu defekti nesējos, kas ražoja klusu datu zudumu vai kritumu izsaukuma brīdī: `claim-extractor.md` :521/:525 (`save_analysis(claims=[])` NEzīmogo dokumentu — vajag `empty_doc_ids`, T5); `daily-routine.md` + `agenti.md` (paralēlā ekstrakcija pa POLITIĶIEM, ne pa dokumentiem — 08-25 likums); `generate_daily_brief_skeleton()` → `generate_daily_brief()`; `validate_quote_against_source()` → `check_quote_against_source()`; workflow `next_steps` uz `bash scripts/deploy.sh` un `.venv` python.
- `CLAUDE.md` T9 / #27 / #118 saskaņoti par balsojumu vektoriem (vēsturiskie paliek, jaunie netiek embedoti) un § Escalation 2 teikums par mazajiem burtiem izlabots.
- **`backlog/dati-db.md` § `review_status` trigera substring-kolīzijas paliek atvērts ar nolūku:** 08-05 gadījumi (#689217 citēts precedents pareizā reģistrā, #689220 `save_analysis` netiešās atsauces frāze) NAV reģistra kolīzijas, tāpēc GLOB tos nesedz.

## 2026-09-05 (1) — pretrunu KANDIDĀTI redzami operatoram: `serve.py` panelis (ieraksts, kas trūka)

Commits `83546921`. Operatora lūgums 2026-09-04 («would be interesting to see contradiction candidates … maybe sometimes publish what and why»); ieviests tajā pašā sesijā, bet CHANGELOG ieraksta nebija — pierakstīts retroaktīvi 2026-09-05.

- **Nesējs ir `logs.details` lauks `rejected_candidates`, NE jauna tabula.** `log_action('contradiction_hunt')` jau ir obligāts solis, kas iet katru dienu, ieskaitot nulles ražas dienas — tieši tas atšķir godīgu nulli no «netika palaists». Piekabinot kandidātus tam, tvērums manto jau ieviestu ieradumu; jauna tabula būtu jauns solis, ko zem slodzes klusi izlaiž (T11).
- **Panelis ir localhost-only pēc uzbūves** (`serve.py` klausās 127.0.0.1), jo noraidīts kandidāts ir nepierādīts apgalvojums par nosauktu cilvēku.
- Kodā: `src/dashboard/views/candidates.py`, `templates/partials/candidates.html.j2`, lauku līgums `.claude/agents/contradiction-hunter.md` § Step 5, rindas prasība `/dienas-rutina` 3. solī. Vārti: `tests/test_dashboard_candidates.py` (8 testi; abi nesošie **mutācijas-testēti** — atslēgas dreifs un kluss malformed zudums abi nogalina testus). Backfill: 09-04 seši kandidāti ierakstīti logs #654968 (`data/rollback_logs_654968_rejected_candidates_2026-09-04.sql`).
- **Kas NAV mainīts:** publicēšanas slieksnis. Kandidāts joprojām nekļūst publicējams bez `@devils-advocate` un operatora apstiprinājuma — mainījās redzamība, ne vārti.

## 2026-09-04 (3) — 09-04 rutīna publicēta; pārskata attēls pārģenerēts pēc izdomāta paraksta

Pierakstīts retroaktīvi 2026-09-05 no commit ziņām (`aaa7effb`, `982f9d62`) — tās dienas ieraksta nebija. `aaa7effb`: «4. septembra dienas pārskats publicēts — 48 pozīcijas, 3 spriedzes, 0 pretrunu». `982f9d62`: «4. septembra pārskata attēls pārģenerēts — viens krēsls, bez izdomāta paraksta» (klase pierakstīta `backlog/repo-higiena.md` § `TEXT_FREE_CONSTRAINTS`).

## 2026-09-04 (2) — `ST!` frakcijas etiķete kanonizēta: 7 448 rindas / 975 balsojumi vairs neizkrīt no koalīcijas kartes

Atrasts, būvējot balsojumu deputātu filtra frakciju grupas (§ 2026-09-04): filtrā parādījās GAN `ST` (14 deputāti), GAN `ST!` (2). Sākotnēji atzīmēts kā „per-balsojuma patiesība, T6 korolārijs — nelabot bez verdikta"; pārbaude to apgāza.

- **Tā ir viena frakcija, ne divas.** `parties.id=9` = `Stabilitātei!`, `short_name='ST'`. Pierādījums: **0 balsojumu**, kuros abas etiķetes parādās vienā `vote_id`; **visi 11** `ST!` deputāti parādās arī zem `ST`; datumu diapazoni pārklājas (`ST` 2022-11-17→2026-04-01, `ST!` 2024-07-25→2025-12-18), un **36 no 153 sēžu dienām nes ABAS** etiķetes. Tātad avota šūnas teksta drifts pa skrāpējumiem, ne vēsturiska atšķirība (frakcijas pārdēvēšana būtu devusi tīru laika robežu).
- **Sekas bija publiskas, ne kosmētiskas.** `ST!` neatbilst ne `parties.name`, ne `short_name`, tāpēc `get_coalition_map()` to atrisināja kā `'other'`, nevis `'opposition'`: **975 balsojumos (12,2 % korpusa)** Stabilitātei! čips renderējās bez opozīcijas iezīmes un frakciju sadalījumā stāvēja nepareizā kārtā (`_enrich_faction_breakdown` šķiro coalition→opposition→other). `FACTION_COLORS` `ST!` arī nesatur.
- **Cēlonis nav trūkstoša normalizācija — tā eksistēja kopš 2026-08-04, bet nepareizā vietā.** Karte `{'ST!': 'ST'}` dzīvoja LOKĀLI `parse_vote_snapshot()` iekšienē, tāpēc abi backfill parseri to nekad neredzēja: `p3_backfill_year_urllib.py::_decode_entry` (JS `voteFullListByNames`, ņēma `parts[2].strip()` verbatim) un `p3_backfill_year.py` (Playwright šūnas). Tie atkārtoti ielika `ST!` rindas PĒC tam, kad 2026-08-04 migrācija (`data/rollback_faction_st_2026-08-04.sql`) tās bija iztīrījusi. Tā ir tieši `CLAUDE.md` „IZPILDĪTS nozīmē, ka kods ir kokā, ne ka tas jebkad nostrādāja" klase — labojums bija merged un uz otra ceļa nekad neizpildījās.
- **Labojums trijās daļās.** (1) Karte pacelta uz moduļa līmeni: `src/saeima/votes.py::FACTION_NORMALIZE` + `FACTION_CELL_VALUES` + `normalize_faction()`; visi TRĪS scrape ceļi to importē un savu karti netaisa. (2) Dati: `UPDATE … SET faction='ST' WHERE faction='ST!'` — 7 448 rindas; pāra rollback `data/rollback_faction_st_canonical_2026-09-04.sql` uzrakstīts PIRMS izpildes un adresē iesaldētu `id` sarakstu, ne `WHERE faction='ST'` (pēdējais skartu arī 50 737 leģitīmās rindas). (3) Vārti `tests/test_faction_label_canonical.py`.
- **Rollback mutācijas-pārbaudīts stiprākajā formā:** uz DB kopijas rollback atgriež `ST`=50 737 / `ST!`=7 448, un SHA-256 pār visiem `(id, faction)` pāriem abās etiķetēs ir IDENTISKS pirms-migrācijas stāvoklim.
- **Vārti pierādīti, redzot tos krītam:** ar atgrieztu `_decode_entry` labojumu `test_both_scrape_parsers_agree_on_every_recognised_cell` krīt ar `{'ST!': ('ST', 'ST!')}` — precīzi tā nesakritība, kas aizbrauca ražošanā. Saucēji nosaukti: 12 atpazītas šūnu vērtības, 11 testi.
- **Pēc labojuma:** korpusā 7 atšķirīgas ne-NULL etiķetes (`AS, JV, LPV, NA, PRO, ST, ZZS`), **0** neatrisinās koalīcijas kartē; `ST` → `opposition`; deputātu filtrā 7 grupas (bija 8), `ST` = 16 deputāti. `check.sh` zaļš (ruff + 2 208 testi). `claims.topic`/`stance` netika skarti, tāpēc re-embed nav vajadzīgs.

## 2026-09-04 — Balsojumu lapa: sēžu grupas, dokumenta konteksts, simbolu leģenda; „Pieņemti %" → trīs skaitļi

Plāns `docs/plans/archive/2026-09-04-balsojumi-parskatamiba.md` izpildīts pilnā apjomā (A–J). Tikai lasāmības slānis — datu modelis, kompaktais JSON un vienīgais renderēšanas ceļš (`bmv1.js::balsojumiArchiveRender`) nemainīti; jauns JSON lauks nav pievienots.

- **Galvenes metrika.** `Pieņemti %` bija procents pār visu korpusu bez redzama saucēja, un tas klusi lasīja katru ne-`Pieņemts` rindu kā noraidījumu. Vietā trīs skaitļi, kas saskaitās līdz „Kopā": **4 695 / 2 717 / 54** no 7 466. `Likums` un `Nod. kom.` paliek „Cits iznākums" — neklasificēto neuzminam (tā pati robeža, kas neļauj tos krāsot sarkanus). Jauns tīrs palīgs `_result_counts()`.
- **TAB 1.** Sēdes dienas grupu virsraksti ar to pašu vārdnīcu (`20.08.2026 · 78 balsojumi · 39 pieņemti · 26 noraidīti · 13 ar citu iznākumu`); kartītes konteksta rinda (dok. nr. + lasījums + „steidzams") un **T14 ķēdes saite** „visi šī dokumenta balsojumi →"; priekšlikumu kartītēm piezīme, ka kopsavilkums ir par likumprojekta virzību kopumā (māsas-`summary` konvencija nosaukta, NE pārrakstīta — operatora lēmums 08-17/18 spēkā); apzīmējumu josla ar `Atturas` skaidrojumu; sesiju filtrs divos soļos (mēnesis → sēde: 169 → 3 opcijas); deputātu filtram frakciju grupas (139 deputāti, 8 grupas, 0 bez grupas); „Tikai dalītie" filtrs.
- **Krāsas leģendā rāda ar īstajiem `.faction-chip` paraugiem, ne vārdiem.** Plānā rakstītais „zaļa = koalīcija, dzeltena = opozīcija" bija nepatiess — CSS dod `--accent` un `--accent-highlight`, un tie ATŠĶIRAS pa tēmām. Aprakstīta krāsa novecotu klusi; paraugs nevar.
- **TAB 2.** Divrindu kolonnu galvene (datums + iznākuma punkts, trīszaru vārdnīca); sticky simbolu leģenda (`NB` vs tukšs vairs nav jāuzmin); tukšā paneļa vietā pēdējās sēdes kopsavilkums ar saiti uz sarakstu (āķis `window.balsojumiSelectSession`); deputāta panelim tvēruma rinda (`sum` ir pār visu ielādēto shardu, ne redzamo diapazonu — skaitīšana NEmainīta, tikai nosaukta); frakciju joslai 4. segments par nebalsojušajiem (saucējs jau saturēja `x`, segmenta nebija — pie daudz NB josla nesanāca 100 %); toggle nosaukumi `Tikai nevienbalsīgie` un `Procedurālie: slēpti/redzami` (agrāk „Procedurālie" neatklāja, vai tos rāda vai slēpj); mobilajā detaļu panelis virs tabulas.
- **Ko izpildīja (nevis „kods ir kokā"):** `tests/test_balsojumi_readability.py` — 27 testa, no kuriem 20 IZPILDA `assets/bmv1.js` node vidē pret sintētisku kompakto JSON (grep pateiktu, ka funkcija eksistē; izpilde pasaka, ka tā strādā). Lapas robežas vārti mutācijas-pārbaudīti: ar atgrieztu labojumu tests krīt ar dublētu `2026-08-20` virsrakstu. Papildus dzīvs pārlūka palaidiens pār īsto renderu (7 466 balsojumi): 0 dublētu virsrakstu pēc „Rādīt vairāk", ķēdes saite dod 2/2 balsojumus par `1518/Lp14`, „Tikai dalītie" dod 162 kartītes, no kurām 162 nes `is-split` čipu (filtrs un čips lieto vienu definīciju `factionIsSplit`), 0 konsoles kļūdu, gaišā + tumšā tēma.
- **Blakusatradums, NElabots:** deputātu filtrā ir gan `ST` (14), gan `ST!` (2) — divas etiķetes vienai frakcijai `saeima_individual_votes.faction` laukā. Faction ir per-balsojuma patiesība (T6 korolārijs), tāpēc to nelabo bez operatora lēmuma; sekas šeit ir tikai divi grupu virsraksti viena vietā.
- `REGEN=1` bāzlīnija: mainījās tikai `balsojumi.html` (`render_baseline_bills.json`). `check.sh` zaļš — ruff tīrs, 2 197 testi.

## 2026-09-03 — 09-03 sesijas atlikums

Pierakstīts retroaktīvi 2026-09-05 no commit ziņas (`5b663970`) — tās dienas ieraksta nebija: «09-03 sesijas atlikums — sēžu manifests 09-03, render baseline hashes». Rutīnas skaitļi commit ziņās nav, tāpēc šeit tos nav; dienas matcher/pipeline karogi dzīvo `backlog/agenti-pipeline.md` (rutīnas 9. solis, `find_inversions` aklā zona, divi precedenta jautājumi).

## 2026-09-02 (9) — Testu pagaidu DB vairs nepiepilda C disku: `tempfile` bāze → `<repo>/.pytest-tmp`

Operatora piezīme no zināšanu bāzes: kopš 08-20 testi bija atstājuši 26k `tmp*.db` failu / 13,7 GB C diska Temp mapē (~1 GB dienā) — 104 testu faili taisa `mkstemp(suffix=".db")`, un uz Windows `unlink` neizdodas, kamēr `get_db()` tur savienojumu atvērtu; teardown to norij.

- **Labojums `tests/conftest.py`:** `pytest_configure` pārceļ `tempfile.tempdir` uz `<repo>/.pytest-tmp` (ceļš no faila, ne ierakstīts); sesijas autouse fixture ieliek to pytest numurētajā mapē (`pytest-of-<user>/pytest-N`, trīs pēdējie palaidieni, slēdzene) un pēc sesijas sauc `gc.collect()`, lai pamestie savienojumi aizveras pirms rotācijas. `.pytest-tmp/` gitignore.
- **Apzināti NE piezīmes 2. solis (`addopts = --basetemp=…`):** fiksētu basetemp pytest iztīra katra palaidiena sākumā, tāpēc divi pārklājoši palaidieni (šodien: `check.sh` fonā + Opus aģenta pytest) sabojātu viens otru. Numurētās mapes to izslēdz.
- **Mērījums:** pirms — 3 testu faili +4 `tmp*.db` C Temp mapē vienā palaidienā; pēc — C Temp +0, `.pytest-tmp/…/sqlite0/` 4 faili. Pilnais `check.sh` (2170 testi): C Temp 339 → 339, `.pytest-tmp` 579 faili / 355 MB — pytest tos rotē pēc trīs palaidieniem (griesti ~1 GB E diskā). Blakus: pilnais palaidiens 14 → 4 min.
- Īstais cēlonis (testējamais kods neaizver savienojumu) paliek; tas vairs neietekmē disku.

## 2026-09-02 (8) — Visi `saeima_vote` stance nu būvēti no kopsavilkuma: 2022–2025 (461 443) + pieci 2026 datumi (2 021); ģenerisko atlikums 0

Operatora «turpināt ar opusiem». Viens Opus aģents izpildīja `apply_saeima_summaries_2026-09-02.py --no-drafts --regen-sessions` pa gadiem (2025 → 2022), orkestrators pārbaudīja skaitļus neatkarīgi.

- **Skaitļi sakrīt ar iepriekš izmērīto tabulu 0 % novirzē:** 2025 — 92 184; 2024 — 151 865; 2023 — 196 434; 2022 — 20 960 (39/43/52/8 sēžu dienas). Pēc tam globālais «Balsoja PAR: <motif>» pie esoša summary = **0** (saucējs: visi `saeima_vote` claims).
- **2025 rollback mutācijas-pārbaudīts stiprākajā formā:** SHA-256 pār visiem 162 694 2025. gada claim `(id, stance)` pēc rollback uz kopijas == pirms-apply kopija. Pārējiem gadiem pirms/pēc skaitīšana (pēc = 0).
- **Rollback kā .gz** (`data/rollback_saeima_stance_regen_{2022,2023,2024,2025,2026b}_2026-09-02.sql.gz`, kopā ~2 MB no ~80 MB SQL; sha256 pārbaudīts pirms .sql dzēšanas). `.gitignore` līdz šim ignorēja `*.gz` — aģentam vajadzēja `git add -f`; pievienota negācija `!data/rollback_*.sql.gz`, lai standarta noteikums «rollback komitējams līdzās» darbotos ar parastu `git add`. DB kopija pirms palaišanas: `data/backup_atmina_pre_stance_regen_2026-09-02.db` (2,4 GB, ignorēta).
- **«lPV» akronīma defekts** (stance ar mazo pirmo burtu pirms akronīma, 1 766 rindas) dzīvoja tikai piecos 2026 datumos (04-01, 04-30, 05-07, 05-14, 05-21), ne 2022–2025; iztīrīts tajā pašā stilā (2 021 stance, `…2026b…`). Atlikums 0 (`stance GLOB '*: [a-z][A-Z]*'`).
- Renders `balsojumi,static`, publish-gate 0 bloķētu, deploy additīvs. BACKLOG § saeima [OPERATOR] ieraksts slēgts.

## 2026-09-02 (7) — Parity audits dabū manifesta vecuma vārtus; tracker prompts prasa visu datuma sēžu UUID savienību

Slēdz 09-02 (6) nosaukto kluso saucēju: `audit_saeima_agenda_parity.py` lasīja manifestu bez datuma un par dienu, kuras manifestā nebija, drukāja «trūkst 0».

- **Manifesta forma mainīta uz apvalku** `{"generated_at": "YYYY-MM-DD", "sessions": [...]}` (`scripts/_p3_extract_sessions_2026-05-26.py` raksta; `src/saeima/manifest.py::load_manifest()` lasa abas formas — kails saraksts dod `generated_at=None`). Apvalks, ne blakusfails: blakusfails var desinhronizēties tieši tajā gadījumā, kura dēļ vārti pastāv. Visi trīs lasītāji pārslēgti (`audit_saeima_agenda_parity.py`, `p3_backfill_year.py`, `p3_backfill_year_urllib.py`).
- **Trīs STOP (exit 2) auditā:** `generated_at` trūkst vai nav datums; ar `--dates` — manifests vecāks par jaunāko pieprasīto dienu; bez `--dates` — vecāks par 14 dienām. Ceturtais: pieprasīts datums bez nevienas manifesta rindas = STOP ar sarakstu, ne tīra diena. Testi `tests/test_saeima_parity_manifest_gate.py` (11), mutācijas-pārbaudīti (abi vārti atsevišķi izņemti → 4 un 3 testi krīt). Dzīvais happy path: `--dates 2026-08-20` tagad redz abas sēdes, 86/86.
- **1(a) izpildīts ar operatora «dari»:** 2026. gada četrām sēdēm (04-16, 04-23, 06-04, 06-18) pārģenerēti **11 945** `saeima_vote` stance — 9 570 ģeneriskie «Balsoja PAR: <motif>» + 2 375 ar veco «lPV» akronīma mazo-burtu defektu (`votes.py` akronīma izņēmums labots agrāk, bet vecās rindas nekad nepārrakstītas). Bez LLM: `apply_saeima_summaries_2026-09-02.py --no-drafts --regen-sessions … --rollback-out` (skripts nu atsakās pārrakstīt esošu rollback failu). Rollback `data/rollback_saeima_stance_regen_2026_2026-09-02.sql` pārbaudīts uz kopijas (0 → 8 817 ģenerisko). Atlikums BACKLOG: 2025. gads (~465k) — paliek operatora lēmums.
- **`saeima-tracker.md` Step 2.0 + 5.bis, `saeima-ingest.md` 2.c:** datums var nest vairākas sēdes (piecas kalendāra etiķešu formas), skrāpē visu UUID savienību; gala vārts salīdzina DB ar to pēc `(vote_date, vote_time)`; STOP tabulā jauna rinda.
- **7928/7938 (08-20) bez `document_nr`:** 7938 = 1064/Lp14 3. las. priekšlikums Nr.2 (Puntulis, stenogrammā unikāls 10/32/31) — `document_nr` ierakstīts; 7928 ir disciplinārs balsojums par Zivtiņa izslēgšanu no sēdes (kārtības rullis 74. p.), NAV likumprojekts, `document_nr` paliek NULL. 8014 pārbaudīts pret 1366_2.pdf — apstiprināts, viens precizējums («vardarbību vai tās piedraudējumu»). Rollback `data/rollback_saeima_summaries_tail_2026-09-02.sql`.

## 2026-09-02 (6) — Saeima: 08-20 sēdes vakars trūka DB (25 balsojumi, t.sk. airBaltic galīgais), abas pēdējās sēdes nu iziet pilnīguma vārtus

Operatora prasība «nolasi visus pēdējos balsojumus un kopsavilkumus» ar četriem Opus `@saeima-tracker` lasīšanas aģentiem; DB rakstīja tikai orkestrators caur diviem skriptiem ar pāra rollback.

- **Manifests bija novecojis (08-01):** `audit_saeima_agenda_parity.py` redzēja 07-23 tikai kā 6+3 balsojumus un 08-20 nemaz — «trūkst 0» ar saucēju 9, kamēr DB glabāja 118. Kalendāra momentuzņēmums pārtverts no jauna, manifests pārģenerēts (2026: 51 sēde; 07-23 = 3 sēdes, 08-20 = 2, 08-21 svinīgā, 09-03 nākamā). Pēc tam: 07-23 = 118/118; **08-20 darba kārtībā 86, DB 61 — ielāde bija apstājusies 18:58:29.**
- **Ielādēti 25 balsojumi** (`ingest_saeima_missing_votes.py`, rollback `data/rollback_saeima_missing_votes_2026-08-20_2026-09-02.sql`): 2 033 individuālās balsis, 100 % sasaiste, 1 733 claims, 0 dublikātu pēc `(vote_date, vote_time)`. Tajā skaitā **airBaltic 1495/Lp14 galīgais balsojums (id 8071, 54/21/1)** — skaitļi sakrīt ar LETA, BACKLOG § airBaltic slēgts; ZZS 11 Pret + 1 Atturas (koalīcijas partija pret savas valdības likumu). Pārējie: 1494/Lp14 Nacionālās drošības likums (steidzamība + 1. las.), 1484/Lp14 vecāku pabalsts strādājošam saņēmējam 50→75 % (visa ķēde līdz galīgajam), Finanšu ministrijas 12 likumprojektu pakete 1382–1393 (PTAC uzraudzība → Latvijas Banka no 2027-01-01; ZZS pret visiem 12, LPV pret 10).
- **08-21 resursu verdikti beidzot IZPILDĪJUŠIES dzīvē** (līdz šim «IZPILDĪTS, bet 0 ielāžu»): jaunajiem 1 733 `saeima_vote` claims `claim_vectors` = 0; `logs` = 22 rindas 22 balsojumiem, ne per-deputāts.
- **60 kopsavilkumi bill-tipa balsojumiem, kam `summary` bija NULL** (07-23: 43; 08-20: 17) — `scripts/apply_saeima_summaries_2026-09-02.py`, melnraksti `data/saeima_summaries_drafts_2026-09-02/`, rollback `data/rollback_saeima_summaries_0723_0820_2026-09-02.sql`. Visi 60 no pirmavota (priekšlikumu tabulas, anotācijas; 1084/Lm14 un 1484/Lp14 skenēti PDF lasīti vizuāli), 0 sentinel. Vārti pirms rakstīšanas: id NULL, neatkārto motif, bez cita balsojuma iznākuma frāzes, diakritika. Atradums, kas attaisno tabulas atvēršanu māsas pārmantošanas vietā: 1366/Lp14 priekšlikums Nr.1 (8014) regulē adopciju (CL 163. p.), ne dzīvnieku statusu, ko apraksta visas māsas.
- **Claim stance pārģenerēti 10 879 rindām** abās sesijās — 4 755 jaunajiem kopsavilkumiem un **6 124 balsojumiem, kam summary JAU bija, bet stance palika ģeneriskais «Balsoja PAR: <motif>»** (kopsavilkums ierakstīts pēc claim ģenerēšanas; piem. 7958 Kiršteina Pret). Bez re-embed (vote claims bez vektora). Forma = `votes.py` (prefikss + mazais sākumburts, akronīma izņēmums).
- **Atklāta klase ārpus šīs sesijas tvēruma, NAV aiztikta:** tas pats ģeneriskais stance pie esoša summary — **477 137 claims / 5 411 balsojumi** visā korpusā (2025-11 līdz 2026-06 sēdes pa 2–6k). Operatora lēmums, sk. BACKLOG § saeima.
- **Aģenta atzīme, neizmeklēta:** 8016 (40/11/20/13) un 8026 (38/27/7/12) glabā `Pieņemts`, kas sakrīt ar formulu bez `Nebalsoja` saucējā — atbilst 08-17 secinājumam, ka etiķete nāk no darba kārtības, ne aritmētikas.
- **Kas šo vārtu neredzēja:** `check_new_session_votes.py` sesijas cron nomira ar 08-21 sesiju; balsojumi upstream parādījās starp 08-23 un 09-02. Manifesta vecums ir otrs klusais saucējs — audita rīks tagad pats saka, cik sēžu tas redz, bet ne, cik vecs ir manifests. **Labots: `saeima-tracker.md` Step 2/5 nu prasa visu datuma sēžu UUID savienību** — Step 2.0 pirms skrāpēšanas uzskaita visas piecas kalendāra etiķešu formas, Step 5.bis salīdzina DB ar šo savienību pēc `(vote_date, vote_time)` un nosauc `audit_saeima_agenda_parity.py --dates` ar prasību, ka manifests ir svaigs. Aģenta STOP tabulā jauna rinda: kalendārā datumam ir vairāk sēžu UUID, nekā tika noskrāpēts.

## 2026-09-02 (5) — A+B retro-labojums sešiem pārskatiem: 23 → 0; ceļā atrastas divas piezīmju novirzes, no kurām vienu neaiztiku

Seši pārskati ar ≥3 atradumiem pēc 6. likuma v2: #419 (08-05) 5, #413 (08-04) 5, #406 (08-03) 4, #491 (08-23) 3, #488 (08-22) 3, #435 (08-08) 3. Pēc labojuma — **0**. Fakti, vārdi un avotu saites nemainīti; mainīta tikai forma (rindkopa → saraksts; sintēze, ko lodziņš jau saka, → viens teikums vai atkrīt).

- **Visiem trīs nesējiem sinhroni:** `context_notes` · `wiki/dailies/` · renderētais HTML (`--only=blog`). Pārbaudīts katram no sešiem, ne pieņemts.
- **Trīs pāra rollback, MUTĀCIJAS-PĀRBAUDĪTI:** palaisti uz DB kopijas — 12/12 rindas atgriezās, un seši pārskati atkal deva tieši 23 atradumus. Tas ir rollback redzēts strādājam, ne tikai uzrakstīts. Skripti: `data/{forward,rollback}_briefs_ab_retro_2026-09-02.sql`, `…_context_notes_ab_retro_2026-09-02.sql`, `…_context_notes_ab_retro_batch2_2026-09-02.sql`.
- **Piezīme #404 (08-03) nesa PĀRLIECINOŠĀKU apgalvojumu nekā publicētā lapa.** DB: «izmeklēšanas iestādes lietā nav iesaistītas». Lapa: «publiski pieejamajos avotos nav ziņu par kādas izmeklēšanas iestādes iesaisti». Kāds bija izlabojis pārskatu, bet ne DB rindu — 2026-08-24 klases spogulis pretējā virzienā (toreiz labojums aizgāja uz DB, ne uz pārskatu). Sinhronizēts uz piesardzīgāko formulējumu.
- **Piezīmes #432 un #433 (08-08) atšķiras no kastītēm SATURISKI, ne formāli, un tās NETIKA sinhronizētas.** Līdzība pret **oriģinālo** kastīti 0,470 un 0,766 — tātad novirze ir pirmsesoša. Pārrakstīšana iznīcinātu append-only tendenču piezīmi (Data Contract #8), tāpēc te «stop beats write»: kura versija ir pareizā, ir operatora izsaukums. Pārējās četras (#490, #492, #486, #487) bija **1,000** pret oriģinālu — tikai šīs dienas formatējums —, un tās sinhronizētas.
- **Metodes piezīme nākamajai reizei:** sadaļā drīkst būt VAIRĀKAS kastītes. Pirmais #419 labojums saglabāja tekstu, kas jau bija sadaļas otrajā lodziņā, jo inspekcijas rīks ņēma tikai pirmo (`re.search`, ne `finditer`). Noķerts ar linteri uzreiz pēc labojuma un izlabots; rīks salabots.

`check.sh` pēc labojuma: **2159 passed**, `check_output` tīrs. Deploy nav veikts — sešas publicētas lapas gaida atsevišķu operatora atļauju.

## 2026-09-02 (4) — 6. likums pāršāva 5×; retro-labojums apturēts pirms pirmās dzēšanas, publicētie skaitļi laboti

Retro-labojums sākās ar #496 (08-24, tolaik 10 atradumi). Pirmais izlasītais pāris to arī apturēja: § airBaltic kastīte saka «likumu Saeima pieņēma 20. augustā, ZZS balsoja pret, strīds iet pa divām līnijām», bet sintēze saka, KURŠ šodien ko teica (Kulbergs, Viļums, Rokpelnis, Švinka, Šuvajevs). **Tas ir papildinājums, ne dublējums** — 6. likuma v1 to sauca par palagu tikai garuma dēļ, un dzēšana būtu iznīcinājusi informāciju.

- **Diskriminators, izmērīts:** 80 garuma-trāpījumi 30 pārskatos → **13 ar ≥3 kopīgiem nosauktiem aktieriem** kastītē UN sintēzē (īsts dublējums), **39 ar NULLI kopīgu** (kastīte = fons, sintēze = dienas runātāji), 28 pa vidu. Garums viens pats ir nepareizi vārti.
- **6. likums v2:** `>40 vārdi` **UN** `≥ SYNTHESIS_SHARED_ACTORS_MIN = 3` kopīgi izsekoto politiķu uzvārdi. Slieksnis kalibrēts pret abiem zināmajiem īstajiem dublējumiem — 2026-09-01 § Imigrācija un § Ukraina stāv tieši uz 3. Uzvārdu kopa satur nominatīvus, tāpēc locītās formas («Edvīna Šnores») nesakrīt un reālā pārklāšanās ir lielāka par izmērīto; slieksnis tādēļ ir konservatīvs, ne agresīvs.
- **Likums tagad ir atkarīgs no uzvārdu kopas, tāpēc tas var IZLAISTIES** — pievienots `rules_skipped` blakus 4. likumam, un tukša kopa dod `rules_run = 4/6`. Bez tā tas būtu tieši tā klase, ko saucējs 2026-08-09 atrada pie 4. likuma.
- **Mutācijas tests atkārtots ar v2, iznākums nemainīgs:** #522 pirms rīta labojuma **5 atradumi** (abi dublējumi tagad ar skaidru pamatojumu «3 kopīgi aktieri»), pēc — **0**. Vārti joprojām krīt tur, kur tiem jākrīt, un vairs nekrīt tur, kur nevajag.
- **Publicētie skaitļi laboti ierakstos (2) un (3).** Bija «23 no 30 krīt, 88 kastītes dublējumi»; pēc v2 — **14 no 30, 34 atradumi kopā** (18 garie bloki + 16 dublējumi), un sliktākais pārskats ir 5, ne 10. `CLAUDE.md` prasa, lai skaitlis nāktu kopā ar vaicājumu, kas to radīja; v1 vaicājums bija nepareizs, tāpēc skaitlis arī.
- **Retro-labojuma tvērums attiecīgi saruka:** operatora izvēlētais kritērijs (sliktākie, ≥5) pēc v2 dod **divus** pārskatus, ne deviņus. Darbs turpinās ar ≥3 joslu (seši: 08-05, 08-04, 08-03, 08-23, 08-22, 08-08) — tas ir tas pats «sliktākie» nodoms uz labotiem datiem.
- **TDD:** 3 jauni testi (kopīgi aktieri ir/nav; likums izlaists bez uzvārdiem), visi redzēti RED. Divi vecie 6. likuma testi pārrakstīti, jo tie kodēja v1 uzvedību; viens mirušais `if False else` zars iztīrīts.

## 2026-09-02 (3) — kastītes līgums sadalīts divos: prozas likumi iekšā, mehāniskie ārā; ligzdotais `<div>` salabots

Ieraksts (2) atsedza, ka `_strip_protected_regions` kastītes karogu izslēdz **pirmais** `</div>`. Skelets raksta ligzdotu formu (`context-box` → `context-label</div>` → teksts → `</div>`), tāpēc karogs nokrita jau uz `context-label` rindas un visa tendenču piezīme klusi nonāca mehāniskajos likumos — pretēji tam, ko solīja docstring. Operatora lēmums: nevis atjaunot veco solījumu, bet sadalīt to divos.

- **Mehāniskie likumi (% atstarpe, anglicismi) kastīti NEREDZ** — teksts nāk verbatim no `context_notes`, un CLAUDE.md § Grammar gate to izņem no laboto vietu saraksta.
- **Prozas likumi kastīti REDZ** — tā ir MŪSU rakstīta tendenču piezīme, tāpēc B garuma forma uz to attiecas. Tas nav teorētisks: 2026-09-01 § Imigrācija palags dzīvoja tieši kastītē (206 vārdi no 355).
- Jauns parametrs `protect_context_box`; prozas skatā izgriež tikai HTML tagu rindas, ne saturu. Ligzdotos `<div>` uzskaita ar **dziļumu**, ne ar pirmo `</div>` — vienrindas bokss joprojām apēd tikai sevi (2026-08-17 regresija paliek aizvērta, tests zaļš).
- **Blakusieguvums, kas pierāda labojumu:** kastīšu vārdu skaits nokrita 207 → 206 un 134 → 133, jo `<div class="context-label">Konteksts</div>` rinda vairs netiek skaitīta par vārdu. Mehāniskais segums #522 ir 91,5 % — tieši kastīšu īpatsvars, godīgi uzrādīts.
- **Mutācijas tests atkārtots pēc labojuma, iznākums nemainīgs:** #522 pirms rīta labojuma 5 atradumi, pēc 0; un `5%` kastītes iekšienē mehāniskajiem likumiem vairs nav redzams (`True`).
- **TDD:** 3 jauni testi. Viens RED (mehāniskie likumi ligzdotajā formā), divi apzināti PIN — tie sargā, lai mehānisko likumu labojums nenoņemtu līdzi prozas segumu. Vecais `test_context_box_protected` paliek zaļš, jo tā fikstūra pārkāpj tikai mehāniskos likumus.
- **Testa palīgfunkcijas off-by-one izlabota:** `_para(n)` deva `n-1` vārdus, tāpēc sliekšņa tests `_para(120)` mērīja 119 un robežu nepārbaudīja nemaz. Tagad tas ir īsts robežas tests.
- **BACKLOG ieraksts, kas dzīvoja vienu stundu, netika atstāts.** Ieraksts (2) to atvēra `backlog/repo-higiena.md`; tā kā tas aizvērts tajā pašā dienā, ieraksts izņemts, nevis atzīmēts ar `[SLĒGTS]` — BACKLOG līgums saka, ka pabeigtais dzīvo šeit, ne tur.
  - **LABOJUMS 2026-09-05: šis teikums bija nepatiess — ieraksts NETIKA izņemts 09-02.** `git log -S'_strip_protected_regions' -- backlog/repo-higiena.md` atgriež tieši vienu commitu (`11329e98`, pievienošana) un nevienu izņemšanu, tāpēc rinda nostāvēja trīs dienas, kamēr šis fails apgalvoja pretējo. Faktiski izņemts **2026-09-05** (sk. § 2026-09-05 (3)). Klase ir tā pati, ko `CLAUDE.md` sauc vārdā: „IZPILDĪTS" pierakstīts pēc nodoma, ne pēc pārbaudītas izpildes.

**Saucējs pēc labojuma nemainījās:** pēdējie 30 dienas pārskati, **23 krīt**. **LABOTS ierakstā (4) — šis skaitlis nāca no pāršaujoša likuma; pēc v2 tie ir 14 pārskati ar 34 atradumiem.**

## 2026-09-02 (2) — A+B dabū koda vārtus; mērījums rāda, ka palaga klase ir 23 no 30 pārskatiem, ne viena diena

Rīta ieraksts (1) A+B ielika aģentu promptos. Tas bija noteikums bez vārtiem — tieši tā forma, ko `CLAUDE.md` sauc par «gate that cannot fail». Tagad `lint_lv_style()` nes divus jaunus likumus, un `RULES_TOTAL` 4 → 6.

- **5. `prose-block-too-long`** — jebkurš prozas bloks pāri `PROSE_BLOCK_MAX_WORDS = 120`. Aizzīmju rinda ir SAVA vienība (`_prose_units()`), tāpēc piecas 40 vārdu aizzīmes iet cauri, bet viena 200 vārdu rindkopa krīt — tas ir viss B jēgas kodols.
- **6. `context-box-synthesis-duplication`** — sadaļai ar konteksta kastīti proza pēc pēdējās tabulas rindas pāri `SYNTHESIS_WITH_BOX_MAX_WORDS = 40`. **Vārti mēra vārdus, ne teikuma zīmes**: LV kārtas skaitļi («24. jūlijā») padara punktu skaitīšanu nedrošu, bet 22 vārdi pret 149 dalās tīri.
- **Mutācijas-pārbaudīts uz dzīviem datiem, abos virzienos.** Pret #522 PIRMS rīta labojuma: **5 atradumi** (207 v un 134 v kastītes, 149 v sintēze, plus abi kastīte+sintēze dublējumi). Pret to pašu pārskatu PĒC: **0**. Tendenču piezīmes atsevišķi: vecās 206 v un 133 v krīt, jaunās iet cauri. Vārti ir redzēti krītam, ne tikai zaļojam.
- **Saucējs pār korpusu — klase ir sistēmiska:** pēdējie 30 dienas pārskati, **23 krīt** (20 par garu bloku + 88 kastītes dublējumi). **LABOTS ierakstā (4): «88 dublējumi» bija 6. likuma v1 pāršaušana — īstais skaitlis ir 34 atradumi 14 pārskatos.** 09-01 nebija slikta diena, tā bija diena, ko operators pamanīja. Vissliktākie: 08-24 (10 dublējumi), 08-03 un 08-04 (7 katrā). **Retro-labojums korpusam NAV veikts** — 23 publicētas lapas ir operatora lēmums, ne higiēna.
- **Jauns likums atsedza vecu defektu, un tas ir pierakstīts, ne apiets** → `backlog/repo-higiena.md` [OPEN]: `_strip_protected_regions` kastītes karogu izslēdz pirmais `</div>`, bet skelets raksta ligzdotu formu (`context-box` → `context-label</div>` → teksts), tāpēc kastītes teksts nonāk lintā, kaut docstring sola pretējo. Pārbaudīts: skeleta forma → redzams **True**, vienkāršā forma → **False**; `test_context_box_protected` lieto tieši to formu, ko skelets neraksta nekad. Tā pati klase, ko `CLAUDE.md` sauc vārdā (checker's tests must read what the writer writes), tikai pretējā virzienā — linteris skenē VAIRĀK, nekā līgums solīja. 5. likuma kastītes trāpījumi pārskatā šobrīd nāk no šī defekta; pēc dizaina to sedz piezīmes atsevišķa lintēšana (`/dienas-rutina` 6. solis), tāpēc labojums vārtus neatvērs.
- **TDD:** 9 jauni testi `tests/test_lv_style.py`, visi redzēti RED (4 kritumi pareizo iemeslu dēļ) pirms implementācijas. Divi esošie testi ar cieti iekodētu `rules_total == 4` atjaunināti uz 6/5.

## 2026-09-02 (1) — «palaga» klase: konteksta kastīte un sintēze pēc uzbūves stāsta vienu dienu divreiz

Operators norādīja, ka 09-01 pārskats vairākās vietās ir nelasāms palags. Mērījums: pārskats #522 bija 4532 vārdi / 36,8 KB pret 15–25 KB iepriekšējās četrās dienās, un § Imigrācija lasītājs pirms pirmās skenējamās rindas izgāja **355 vārdus nepārtrauktas prozas** — 206 vārdu konteksta kastīte plus 149 vārdu sintēze zem tabulas, ar tiem pašiem astoņiem aktieriem tajā pašā secībā un gandrīz identisku noslēguma frāzi.

- **Cēlonis ir strukturāls, ne rakstīšanas gaume.** `generate_daily_brief()` (skelets) konteksta piezīmes izvelk ar `routine_day_window(date)` (`src/briefs.py:431`), tātad kastītē **vienmēr** ir TĀS PAŠAS dienas piezīme — nekad iepriekšējo dienu fons. Aģents zem tabulas raksta sintēzi par to pašu dienu, tāpēc dublēšanās ir iebūvēta skeletā. Tā parādās tieši un tikai tajās sadaļās, kurām ir tendences piezīme (09-01: Imigrācija un Ukraina; pārējās piecas sadaļas bija 48–66 vārdi, t.i. normā).
- **Jauns noteikums A+B** — [`brief-shared-rules.md`](operations/agenti/brief-shared-rules.md) § Prozas bloku forma, ar nesējiem `@brief-writer`, `@weekly-brief-writer`, `/dienas-rutina` 6. solī un divām jaunām latiņām [`quality-bars.md`](operations/quality-bars.md). **A:** ja tēmai ir kastīte, sintēze zem tabulas ir ne vairāk kā VIENS teikums un tikai par to, kā kastītē nav; ja jaunā nav nekā — rindkopa atkrīt. **B:** katrs aģenta rakstīts prozas bloks ≤120 vārdu, 4+ nosaukti aktieri iet sarakstā (viens aktieris = viena rinda), nevis semikolu virtenē. Tendences piezīme pati iziet B, jo tā nonāk lapā verbatim.
- **Saucējs pašpārbaudē** (`@brief-writer` 18. punkts): bloku skaits · garākā bloka vārdi · cik pāri 120; plus cik tēmām bija kastīte un cik no tām sintēze pārsniedza vienu teikumu (jābūt 0). «Pārskats ir pārskatāms» bez šiem skaitļiem ir vārti, kas nevar nokrist.
- **#522 pārtaisīts retroaktīvi** (nav tikai nākotnes noteikums): Imigrācijas sintēze noņemta pilnībā, Ukrainas 64 → 22 vārdi (paliek Bražes atsevišķais Ukrainas/sankciju izteikums, kas kastītē nebija), abas kastītes un Koalīcija vs Opozīcija rindkopa pārliktas sarakstā. 36 815 → 35 334 zīmes; renderētajā HTML Imigrācijas kastītē 5 `<li>`, Ukrainas 4, KvO 3. Fakti, vārdi un secība nemainīti.
- **Trīs nesēji sinhronizēti vienā piegājienā** (tā pati klase, kas 08-24 nostrādāja tikai daļēji): `context_notes` #520/#521/#522 · `wiki/dailies/2026-09-01.md` · `blog/2026-09-01.html`. Pāra skripti `data/forward_brief522_notes520_521_ab_forma_2026-09-02.sql` + `data/rollback_…`; rollback uzrakstīts PIRMS mutācijas.
- **Tendenču piezīmes tika pārformatētas, ne pārrakstītas** — Data Contract #8 «append-only» sargā evolūcijas signālu, un visi fakti, vārdi un secība palika; procedūra ņemta no `brief-shared-rules.md` noteikuma «piezīmes labojums iet trīs vietās». Ja lasījums ir stingrāks, rollback atgriež visas trīs rindas.
- **`lint_lv_style` noķēra divas reālas kļūdas sociālajos melnrakstos** (abi Reddit posti sākās ar `1. septembr…` → `<ol>` slazds) un vienu manu faktu kļūdu tam blakus: 2026-09-01 ir **otrdiena**, ne pirmdiena. `check.sh` 2146 passed.

## 2026-09-01 — 09-01 dienas rutīna: 810 doku, 52 pozīcijas, pārskats #522 publicēts

Pierakstīts retroaktīvi 2026-09-05 no commit ziņām — tās dienas ieraksta nebija. `ae8f1f6e`: «2026-09-01 dienas rutīna — 810 doku, 52 pozīcijas, pārskats #522 publicēts». `e14f838b`: «wiki_sync pārlaists pēc 09-01 ekstrakcijas». `9ffd149c`: «vienu dienu novēlota pārskata footer vairs nerāda nulli». (#522 palaga klase un tās retro-labojums pierakstīti atsevišķi § 2026-09-02 (1)–(5).)

## 2026-08-31 — 08-31 rutīna + nedēļas pārskats

Pierakstīts retroaktīvi 2026-09-05 no commit ziņām — tās dienas ieraksta nebija. Koka pēdas: `23121af4` («08-28..08-31 rutīnu atceļamie ieraksti nonāk kokā»), `7b5a23c3` («08-29..08-31 forward skripti pievienoti pie saviem rollback») un `b05b79e2` («pievienots trūkstošais forward skripts claim 704308 dzēšanai»). Skaitļi commit ziņās nav nosaukti, tāpēc tos šeit nav — nemēģini tos atvasināt no `data/` melnrakstiem bez vaicājuma.

## 2026-08-30 — 08-30 rutīna

Pierakstīts retroaktīvi 2026-09-05 no commit ziņām — tās dienas ieraksta nebija. Koka pēdas: `23121af4` un `7b5a23c3` (abu ziņas sedz 08-29…08-31 rutīnu labojumu rollback un forward skriptus). Skaitļi commit ziņās nav nosaukti.

## 2026-08-29 — 08-29 rutīna

Pierakstīts retroaktīvi 2026-09-05 no commit ziņām — tās dienas ieraksta nebija. Koka pēdas: `23121af4` un `7b5a23c3`. Skaitļi commit ziņās nav nosaukti.

## 2026-08-28 — 08-28 rutīna

Pierakstīts retroaktīvi 2026-09-05 no commit ziņas — tās dienas ieraksta nebija. Vienīgā koka pēda ir `23121af4` («08-28..08-31 rutīnu atceļamie ieraksti nonāk kokā»); skaitļi commit ziņās nav nosaukti.

> **Kāpēc šie pieci ieraksti izskatās tukši, un kāpēc tas tā paliek.** Per-dienas rutīnas ieraksti bija konvencija līdz 08-27 (08-24 (1), 08-25 (4), 08-26, 08-27 (5) visi tādu nes); pēc tam tā klusi nokrita, un 2026-09-05 audits atrada **septiņu rutīnas dienu caurumu** (08-28, 08-29, 08-30, 08-31, 09-01, 09-03, 09-04) failā, kas ir atbilde uz jautājumu «kas šo izpildīja?». Aizpildot to 09-05, skaitļus atvasināt vairs nav no kā — commit ziņās to nav —, tāpēc šeit stāv tikai tas, kas ir pierādāms. Tukša rinda ar nosauktu avotu ir godīgāka par rekonstruētiem skaitļiem, un caurums vairs neizskatās pēc dienām, kad nekas nenotika.

## Arhīvs (2026-04 — 2026-08-27)

Vecākie ieraksti pārcelti uz [CHANGELOG-arhivs.md](CHANGELOG-arhivs.md) (2026-07-21 aprīlis+maijs, 2026-08-01 jūnijs, 2026-08-02 jūlijs, 2026-08-05 agrīnā daļa 07-31→08-02, 2026-08-09 diena 08-03, 2026-08-19 diena 08-04, 2026-08-23 dienas 08-05—08-09, 2026-08-24 dienas 08-10—08-16, 2026-08-27 diena 08-17/18, 2026-08-27 dienas 08-18—08-19, 2026-08-27 dienas 08-20—08-21, 2026-09-05 dienas 08-24—08-27; pilns saturs + visi enkuri tur). Zemāk enkuru-stubi ierakstiem, uz kuriem atsaucas `CLAUDE.md` / aģentu prompti — virsrakstu teksts saglabāts identisks, lai saites turpina strādāt.

## 2026-07-29 — Kurētās analīzes `standalone: true` paterns + NVO dotāciju lapa

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Kurētās analīzes](CHANGELOG-arhivs.md#2026-07-29--kurētās-analīzes-standalone-true-paterns--nvo-dotāciju-lapa)

## 2026-07-27 — Matcher B2+D2+H: vārda robežas, paplašinātais priekšvārda veto, @handle formas

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Matcher B2+D2+H](CHANGELOG-arhivs.md#2026-07-27--matcher-b2d2h-vārda-robežas-paplašinātais-priekšvārda-veto-handle-formas)

## 2026-07-24 — T7 slēgts: brief skelets vairs klusi nemet tēmas (Pārējās tēmas tabula)

→ pilnais ieraksts: [CHANGELOG-arhivs.md § T7 slēgts](CHANGELOG-arhivs.md#2026-07-24--t7-slēgts-brief-skelets-vairs-klusi-nemet-tēmas-pārējās-tēmas-tabula)

## 2026-07-23 — Stingrā CSP: drošības galvenes + viss inline JS uz assets/*.js

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Stingrā CSP](CHANGELOG-arhivs.md#2026-07-23--stingrā-csp-drošības-galvenes--viss-inline-js-uz-assetsjs)

## 2026-04-25 — Strukturālā sanācija: pub_at meta tag fix + Saeima vote-as-document anti-pattern noņemšana

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Strukturālā sanācija](CHANGELOG-arhivs.md#2026-04-25--strukturālā-sanācija-pub_at-meta-tag-fix--saeima-vote-as-document-anti-pattern-noņemšana)

## 2026-04-25 — Commentator demotion + profila X subtaba

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Commentator demotion](CHANGELOG-arhivs.md#2026-04-25--commentator-demotion--profila-x-subtaba)

## 2026-04-23 — `social_accounts.feed_type` (relay vs first_party)

→ pilnais ieraksts: [CHANGELOG-arhivs.md § feed_type](CHANGELOG-arhivs.md#2026-04-23--social_accountsfeed_type-relay-vs-first_party)

## 2026-04-23 — Komentētāji (speaker_id on claims)

→ pilnais ieraksts: [CHANGELOG-arhivs.md § Komentētāji](CHANGELOG-arhivs.md#2026-04-23--komentētāji-speaker_id-on-claims)

## 2026-04-11 — claim_type split (`position` vs `saeima_vote`)

→ pilnais ieraksts: [CHANGELOG-arhivs.md § claim_type split](CHANGELOG-arhivs.md#2026-04-11--claim_type-split-position-vs-saeima_vote)
