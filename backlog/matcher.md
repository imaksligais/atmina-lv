# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## Matcher / atribūcija

> Konsolidēts 2026-08-01 — kolīziju darbs bija izkaisīts pa trim sadaļām. Kodā ievieso vārtus tur `scripts/eval_matcher_collisions.py` (FP≤3, zelts≥1260); slēgtie per-gadījumi dzīvo CHANGELOG § 2026-08-01.

### [OPEN] Stale junction atlikums — 50 rindas bez vārda tekstā (23 doki) un 23 vēlākas piesaistes

Apakšvirknes klase slēgta (commits `2cd75bba`, `5669fb66`, `15ec5079`, `b8349d18`, `1775832c`). `scripts/audit_stale_politician_links.py` 2026-09-25: 9 973 doki pārbaudīti, 559 rindas saistītājs vairs neradītu, no tām 184 «teksts nepamato», **DEFEKTI 0**. Paliek četras grupas:

- **(1) `varda_nav_tekstā` — 50 rindas / 23 doki (09-22: 51).** Tās NEgaida `avoti.md` truncated kampaņu: tās atlase (`word_count<90`) sedz tikai 1 no 23 dokiem. 42838 (313 vārdi) un 42843 (365) nes 26 no 50 rindām; seši doki ir 2 494–18 980 vārdu (vestnesis, dati.cvk), tātad birka «nogriezts» tur nav pārbaudīta (T18). *Rīcība:* mērķēta pārlāde 22 dokiem vai sešu garo doku lasīšana; nekad nedzēst uz klasifikatora vārda (T19).
- **(2) `piesaiste_velak` — 23 rindas / 22 doki.** *Rīcība:* noskaidrot, kurš koda ceļš tās raksta.
- **(3) `teksts_nomainits` — 35 rindas / 13 doki.** `_reconcile_junction_suspects` karogo tikai turpmākās pārrakstīšanas; vēsturiskās rindas retrospektīvi nav karogotas. *Rīcība:* vienreizējs `suspect_at` pēc operatora vārda. Blakus: `SELECT COUNT(*) FROM document_politicians WHERE suspect_at IS NOT NULL` → **38** (2026-10-21; pēc `DATE(suspect_at)`: 10-01 7, 10-04 19, 10-05 9, 10-14 3); 10-01 rindas ir rokas `suspect_at` (LIELO burtu (b)); jāpārbauda, vai 10-04/05 rindas rakstīja `_reconcile_junction_suspects` — līdz tam vārts pierādīts tikai testos (`tests/test_junction_suspect_flags.py`).
- **(4) CVK lapu organizāciju rindas pēc 2026-10-14 izņēmuma** (verdikts C7, slēgtā NBS pid=204 ieraksta atlikums): atstātas 3 pid 204 `mentioned` + 4 citu organizāciju rindas CVK lapās, nelasītas. Jaunas `src.roles.drop_cvk_organization_links` vairs nerada. *Rīcība:* izlasīt 7 rindas; dzēst tikai ar pāra rollback.

*Īpašnieks:* operators. Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_matcher.md`.

### [OPEN] Releja kanāla dokuments ar citā plūsmā piesaistītu autoru (`subject`) netiek pārbaudīts pieminējumu meklēšanā

Agrāk «Junction abu virzienu izmeklēšana» (divi spoguļdefekti vienā mehānismā). Pilnais naratīvs ar instanču vēsturi: [`docs/audits/2026-10-01-backlog-narativi.md`](../docs/audits/2026-10-01-backlog-narativi.md).

**(b) Iztrūkstošais virziens — first-party `subject` dokiem nebija mention pass.** IZPILDĪTS 2026-08-18 (`_link_first_party_mentions()` `src/social.py`, loma cieti `mentioned`; `aa379211`); vēsturiskais backfill 2026-10-01 (CHANGELOG 2026-10-01 (2)). **Paliek atlikums:** relay-atnests doks ar cross-feed autora `subject` saiti izkrīt no `matcher.py:895` atlases tāpat — tā pati klase pa relay ceļu, verdikts to nesedza.

_(a) Fantoma `mentioned` (svešs tvīts laika joslā) — IZPILDĪTS, CHANGELOG 2026-10-14 (15)–(16)._

### [OPERATOR] Junction lomas apgrieztas pārstāstos — `mentioned` runātājs nesasniedz rindu

**2026-10-14 (verdikti):** (1) instances demotētas (120049, 120019, 120708/684/676, 124194, 124250, 129930, 125359, 126705, 127368; 123460 Valainis → `mentioned`); 120749 — pid 200 jau `mentioned`; 127358 Kulbergs → `subject`. `data/rollback_verdikti_h1_2026-10-14.sql`. Paliek (3).

> **Stāvoklis.** Klase ir **viens dizaina lēmums**: `role='subject'` tiek piešķirta pēc vārda klātbūtnes tekstā, ne pēc runas akta. Kopš 2026-09-07 `src/roles.py` ir vienīgais īpašnieks jautājumam, kurš drīkst nest `subject` (abi bulk-rakstītāji iet caur to); releja mediju sloti (`organization` + `relay`) un @Brivibas36 kailie retvīti `subject` vairs nerada (`tests/test_subject_role_guards.py`; CHANGELOG 2026-09-07 (7)). (2) LETA apakšpunkts SLĒGTS 2026-09-07. Vēsturiskās 3 027 rindas demotētas 2026-09-06 (CHANGELOG arhīvs 2026-09-06 (2); `data/fix_grupaE_subject_demote_*`). Spoguļa klase § Junction abu virzienu ar nolūku NAV apvienota — cits mehānisms un cits saucējs. **Cena:** `reviewed_at` ir per-DOKUMENTS, tāpēc nepareizs `subject` aizver dokumentu arī īstajiem runātājiem (CLAUDE.md § Schema invariants). Pilnais naratīvs: [`docs/audits/2026-10-01-backlog-narativi.md`](../docs/audits/2026-10-01-backlog-narativi.md).

**(1) `subject` lomas inflācija personām — vispārīgais noteikums NAV ieviests (verdikts A1, 2026-10-01).** Mērījums: `speaks()` apstiprina tikai 84,3 % claim-ražojošo web `subject` pāru (1 492/1 770); variants «nomainīt, ja runā cits» 93,9 % (< 97 % vārti). Reālos runātājus jau atgūst rutīnas citētā runātāja josla (`quoted_speaker.recovery_survey`). 9 zināmās instances demotētas (`data/rollback_subject_inflation_9_2026-10-01.sql`); 384 atturētās rindas ievietotas kā `mentioned` (`data/rollback_held_subject_as_mentioned_2026-10-01.sql`).
**(3) Junction lomas apgrieztas pārstāstos — `mentioned` runātājs nekad nenonāk ekstrakcijas rindā.** Sakne doc 78085: rinda iet tikai pa `role='subject'`; tā ir vispārīga LV ziņu uzbūve, ne LETA klase. 09-07 vārts demotē bez paaugstināšanas, tāpēc 962 dokos, kur relejs bija vienīgais subjekts, citētie runātāji joprojām nav sasniedzami.

- **Rīks — lieto to, ne pierakstīto procentu:** `scripts/audit_junction_role_inversion.py` + `/audit-integrity` 15. pārbaude (bāzlīnija 2026-09-25, 90 d: `checked=2635 flagged=270`).
- **Lēmums 2026-08-04: (b) + backfill, 1.–5. solis ieviests** (`729aa27e`, `docs/plans/2026-08-04-junction-inversion-queue-fix.md`); viļņi 08-05 un 08-06 izpildīti (CHANGELOG arhīvs 2026-08-05/06). 2026-08-16 vienā dienā atgūtas 6 pozīcijas no 4 dokiem (88345, 88820) — klase ir smagāka, nekā ~1,4 doku dienā liek domāt.
- **Atvērts — 6. soļa turpinājums:** partijas pa ≤12 pāriem no `pending_quoted_mentioned(db, days=90)`, atsevišķi no dienas rutīnas. Nākamie mērķi: doc 76625 Rinkēvičs; Kulberga kokrūpnieku web trio 71412/71395/71371 (visos `mentioned`, 0 pid=10 claims); doc 72401 Rokpelnis (`subject`, 0 claims) + 6 līdziesniedzēji `mentioned` (74, 109, 89, 73, 145, 162).
- **Instances no handoffiem 10-05…10-09:** Rinkēvičs `mentioned` 121897 un 126730; Abu Meri `mentioned` 125775/125808/125829, kaut raksts ir par viņu; Pujāts (pid 246) `mentioned` 4 dokos, kur runā pats; Latkovskis doc 115440 `extracted_at` NULL; 80 politiķi, kurus 2026-09-23 pazemināja uz `mentioned`, nav atgūti.
- **Detektora FP/empty klases:** neizsekots komentētājs par daudziem politiķiem (76612); pasīvais saturs bez nostājas (76611); divu lēcienu pārpublicēts citāts (73172); cross-source verbatim dublikāti (lielākais empty cēlonis).
- **Ekspozīcijas vaicājums:** šodien zīmogotie web doki, kuros tracked politiķis ir `mentioned` un viņam no tā doka nav claim (08-16: 26 pāri pār 10 dokiem, trāpījumi ~3 no 10).
- **Procedūra atgūšanas aģentiem:** padod dokumenta ID un liec LASĪT, nekad nepadod satura kopsavilkumu — trīs reizes no trim nodotais apraksts bija nepilnīgs.
- **Blakus klase ārpus verdikta tvēruma:** `feed_type='relay'` ir arī 7 žurnālistiem un 6 neaktīvām personām. Lapsa (pid=57) nes 3 219 twitter `subject` rindas no kailiem RT ar `@Lato_Lapsa` (atbildes viņam, ne viņa runa). Vārta paplašināšana uz jebkuru `relay` kontu ir viena rinda `scope.relay_media_pids()` vietā; cena — šo žurnālistu profila X apakšcilne pārstāj papildināties. *Īpašnieks:* operators. **Mērījums 2026-10-05** (backloga sweep): Lapsas 99 rindas `subject` pāri → 0 pozīciju (visi aģenti: «relay konts nekad nav runātājs»), ~6 aģentu darbs veltīgi. Variants ar mazāku cenu: paplašināt tikai rindas predikātu `src/scope.py::_QUEUE_POLITICIAN_TEMPLATE` uz `journalist`+`relay` (ne `relay_media_pids()`, ko lasa arī junction rakstītājs) — X apakšcilne nemainās, jo tā lasa junction bez šī predikāta; zaudē tikai parakstīta viedokļraksta izņēmumu (`sloti.md`), ko var atstāt `web` platformai.

**2026-10-21 (7):** stenogrammās 657 esoši runātāju pāri joprojām `mentioned` (jaunie kopš 10-21 — `subject`). Paaugstināt? UPDATE ierakstītu 657 apspiešanas ar `reason='auto-demote'` — vispirms izvēlēties ceļu. Noklusējums: atstāt.

### [OPEN] T1 locījumu kolīziju klase (2026-08 gadījumi)

**(a) Lāce/Lācis, (b) Uģis Krastiņš un (d) Ceriņš/„ceriņu sfinga" SLĒGTI 2026-08-05** — visas trīs saites dzēstas ar satura pierādījumu + šauri `negative_patterns`; harness FP 1 / zelts 1339; pēda CHANGELOG 2026-08-05, rollback `data/rollback_t1_collisions_lace_krastina_cerins_2026-08-05.sql`.

**Paliek atvērts — sistēmiskais kandidāts:** `scripts/audit_matcher_name_forms.py` sweep pār fem `-e` / masc `-is` pāriem (`_latvian_surname_inflections('Lāce')` dod `Lāci` ≡ `Lācis` akuzatīvs; B2+D2+H šo klasi strukturāli neķer — korekts vārds, korektas robežas — tāpēc tā atkārtosies ar citiem pāriem). **Saucējs 2026-09-25:** `_latvian_surname_inflections` pār visiem ne-organizāciju `-e` uzvārdiem — **28 no 28** ģenerē `X-i`, kas ir `X-is` akuzatīvs (Lāci/Lācis, Pūci/Pūcis, Zīli/Zīlis, Priedi/Priedis, Kalnieti/Kalnietis…); sweep skriptā nav (`grep -n "pair\|masc" scripts/audit_matcher_name_forms.py` → nekā). *Rīcība:* sweep = korpusā skaitīt `X-i` trāpījumus, kuru tuvumā ir vīriešu priekšvārds, un tikai tad lemt par kodu. *Īpašnieks:* operators. Daģa (id=81) brīdinājumi pārcelti uz `wiki/operations/seeding.md`.

**Atvērts 2026-10-05:** forma «Šleseri» ir gan Danas Šleseres akuzatīvs, gan ģimenes daudzskaitlis (3 doki) — lēmums par formu `name_forms` nav pieņemts. *Īpašnieks:* operators.

### [OPERATOR] Liepiņas `negative_patterns` — citi Liepiņi (~85 doki)

**2026-10-14 (verdikti):** Krasta: `Krasta iel` + 5 rindas dzēstas. Liepiņa: 4 rindas + 34376 (cita Linda) dzēstas (69298/74346 jau 10-01); KNAB paterns noņemts (veto 5/5 īstus dokus), «izsludināta par mirušu» paliek; piesaistīti 33417, 54279, 108514, 108551, 131913. Paliek tikai (ii) citi Liepiņi.

Paterni ieviesti 2026-08-18 (`data/{fix,rollback}_krasts_negative_patterns_2026-08-18.sql`, `data/{fix,rollback}_liepina_negative_patterns_2026-08-18.sql`). Krastas rindas (pid 108) un Liepiņas (iii) rindas 2026-10-21 DB vairs nav.

- **Liepiņa (pid=107):** (ii) ~85 doki ar citiem Liepiņiem (Sanda 19, Zaiga 17, Modris 13, Jānis 9, Kristīne 6 u.c.) — pilnvārdu paterni, katram ko-okurences pārbaude ar Lindu.

*Īpašnieks:* operators (`negative_patterns` nekad neauto-pievieno). Pierādījumi: `docs/audits/2026-09-25-backlog-triaza/triage_matcher.md`.

### [OPERATOR] Konteksta kolokācijas dizains — Meļņa, Valaiņa un Bērziņa klase vienā mehānismā

**2026-10-14 (verdikti):** 95063 dzēsts, 123460 → `mentioned` (tekstā abi Valaiņi). Mehānisms joprojām nav — rescan tos atjaunotu.

> **Atvērts 2026-09-07** (verdikti 30 un 33, CHANGELOG 2026-09-07 (4)): trīs gadījumi ir viena klase — «NĒ atsevišķam labojumam, JĀ kopīgam risinājumam». Pilnais naratīvs: [`docs/audits/2026-10-01-backlog-narativi.md`](../docs/audits/2026-10-01-backlog-narativi.md).

**Klase.** Virkņu līmenī neatrisināmas kolīzijas, kur atšķirīgais signāls ir blakus stāvošais amata apzīmējums, ne vārda forma:

- **Meļņi.** pid=157 Kaspars Melnis (ZZS) nes kailo formu `Melnis`, pid=224 Raivis Melnis (aizsardzības ministrs) — nē. Datu daļa SLĒGTA 2026-09-07: 9 junction rindas pāratribuētas (`data/{fix,rollback}_melni_reattrib_2026-09-07.sql`), neviena no 54 pid=157 pozīcijām nepieder Raivim Melnim.
- **Valaiņi.** pid=25 Viktors Valainis pret LBTU docentu ar identisku vārdu un uzvārdu — ne D2, ne priekšvārda veto, ne `negative_patterns` to nešķir. Instances: doc 95063 (rinda dzēsta 10-14) un doc 123460 (tekstā abi Valaiņi, 10-14 → `mentioned`); `match_politicians` tās atjaunotu.
- **Bērziņi.** pid=146 Andris Bērziņš pret dziedātāju doc 64681: junction rindu nav, bet `match_politicians(64681)` → `(146, 'subject')` — eval vienīgais atlikušais B2D2H `fp_links=1`. Otrā instance doc 110049 (SM valsts sekretāra vietnieks **Kaspars** Bērziņš): `negative_patterns` veto noķer tikai pirmo pieminējumu, un 4× kails «Bērziņš» saiti izveido no jauna; junction dzēsts 2026-09-23 (`scripts/fix_operator_verdicts_2026-09-23.py`, `data/rollback_operator_verdicts_2026-09-23.sql`). Papildkandidāts: **`negative_patterns` trāpījums dokā bez neviena pilnvārda trāpījuma = kailais uzvārds šajā tekstā pieder citam** → kailās formas šim dokam nesaista.

**Mehānisma kandidāts:** kails uzvārda trāpījums + **±1 teikumā amata apzīmējums, kas sakrīt ar CITA tracked politiķa `role`** → nesaistīt, bet pierakstīt kandidātu operatora izskatīšanai («stop beats write»; `negative_patterns` nemainās).

**Eval segums (2026-09-25):** `scripts/eval_matcher_collisions.py` 32 marķētajos FP ir Bērziņa gadījumi (62139, 64681, 74402) un Valainis-Oskars (62152), bet nav Meļņa, 95063 vai 110049 — labojums tiem eval rezultātu nekustinātu. **Priekšnosacījums pirms jebkādas `negative_patterns` maiņas kailajai `Melnis` formai: eval korpusā jāieliek Meļņa gadījums.**

**Eval segums + mērījums (2026-10-14, CHANGELOG 2026-10-14 (13)):** FP korpusā +11 (9 Meļņi, 95063 Valainis-docents, 110049 Kaspars Bērziņš) → 43. Pašreizējais matcher (B2D2HC) piesaista tikai 95063 (fp_links 1→2, vārti ≤3 tur); 9 Meļņi un 110049 nav piesaistīti PAT bez `negative_patterns` (counterfactual 29→30) — Meļņus nosedz kopīgā-uzvārda sargs (abi izsekoti), 110049 — svešā priekšvārda veto. **Secinājums:** kailās `Melnis` formas `negative_patterns` maiņa šos 9 nekustinātu; atvērtā klase ir tikai pilnvārda dvīņi ar neizsekotu vārdabrāli (Valainis-docents, Bērziņš-dziedātājs/aktieris). Mērījums `docs/audits/2026-10-14-datu-kvalitate/_homonym_role_scan.py` (web 365 d, abi bloki vienā skriptā): 8 218 saites bez NOMINATĪVA pilnvārda formas dokā (deklinēti pilnvārdi neizslēgti — izlasē ~5/12 tādi, tātad īsti kailu saišu ir mazāk); «cita politiķa amats ±1 teikumā» karogo 4 627 (izlasē 10 pēc fragmenta — visas pareizas saites, nederīgs); «svešs amats ≤3 vārdi pirms uzvārda» 946 (izlasē 12: 1 pārbaudīta pilnā tekstā, 11 pēc fragmenta — neviena acīmredzami kļūdaina; kontroļu 95063/25 un 110049/146 saites jau dzēstas, tāpēc korpusā nav). Amata kolokācija virkņu līmenī nav dzīvotspējīgs mehānisms; pilnvārda dvīņiem paliek domēna leksikons (eval A2) vai operatora kandidātu saraksts.

*Paliek:* domēna leksikons vai operatora kandidātu saraksts (mērījums 10-14). *Īpašnieks:* operators.

### [OPERATOR] Lūša ≤4 zīmju formas (T1) — `Lūsi` dala arī pid 206 Lūse

**2026-10-14 (verdikti):** pid 206 `negative_patterns` = 6 formas ieviestas; cena: nākamais rescan atmetīs 50079 (Lūse + Viesturs Lūsis, `mentioned`, 0 claims — INSERT rollback galvā). Paliek: ≤4 formas pie reaktivācijas.

pid=174 Toms Lūsis: `_latvian_surname_inflections('Lūsis')` ≤4 zīmēm → `['Lūsi', 'Lūša']` — apakšvirkņu bumbas (CLAUDE.md § Īsās ģenerētās formas). Slots ir `inactive` (`name_forms='[]'`), tāpēc šodienas cena ir zema, bet reaktivācija to uzreiz paceltu. `Lūsi` ģenerē arī pid 206 Mairita Lūse (arī `inactive`) — reaktivējot jebkuru no abiem, forma kolidē starp diviem izsekotiem cilvēkiem. *Rīcība:* karogot operatora izskatīšanai, nekad neauto-noņemt. *Īpašnieks:* operators. **2026-10-05:** Lūse (206) atkal `tracked` (15. Saeima); 6 svešas saites dzēstas (`data/rollback_fix_links_2026-10-05b.sql`: Toms Lūsis ×4, «Lūsija», «T. Lūse»).

### [OPEN] Citētā runātāja joslas atlikums — bezpersonisko atribūciju veto kandidāts

Substring-defekts (`raksta` iekš `saraksta`) slēgts 2026-08-05. Paliek kandidāts **bezpersonisko atribūciju veto**: `teikts … programmā/paziņojumā` citē dokumentu, ne cilvēku, tāpēc tuvumā esošs nominatīvs nav runātājs (`grep -n "programm\|paziņojum" src/quoted_speaker.py` → veto nav). Pirmais saucējs 2026-09-25: web doki 90 d = **7 933**, no tiem ar regex `teikts … (programmā|paziņojumā|dokumentā|ziņojumā|vēstulē)` = **193** (2,4 %). *Nākamais solis:* krustot 193 ar `audit_junction_role_inversion.py` karogiem (270), tad lemt par veto. *Īpašnieks:* operators.

**Otrs robs (2026-10-11):** `recovery_survey` nepamana runātāju bez nominatīva blakus («pauda ministrs» — Smiltēns doc 131912, pievienots ar roku).

### [OPERATOR] `negative_patterns` apkalpo divus filtrus (VAD haystack + ziņu matcher) + Kulberga `vad_disambig` hinti

**2026-10-14 (verdikti):** Kulberga hinti papildināti («Valsts kanceleja», «Ministru prezidents»). Paliek strukturālais jautājums (atsevišķa kolonna).

- **Problēma:** `tracked_politicians.negative_patterns` lasa divi semantiski atšķirīgi patērētāji — `src/vad/declarations.py:92` (`_row_passes_disambig`, haystack = institūcija + amats) un `src/matcher.py:421` (`match_politicians`, `any(p in text …)` uz VISU dokumentu → viss doks veto). Kulberga «Valsts policija» (seedēts VAD homonīmam) 60 dienās veto 66/66 ziņu dokus par premjeru; paterns noņemts 09-13, bet klase paliek — 46 politiķiem ir netukši `negative_patterns`.
- **Rīcība:** atsevišķa kolonna VAD haystack paterniem vai `match_politicians` veto tikai teikuma/loga robežās; līdz tam katrs VAD motivēts paterns ir ziņu matcher risks. Blakus: pid 10 `keywords.vad_disambig` = `["Latvijas Republikas Saeima", "Saeimas deputāts"]` — hinti papildināti 2026-10-14 («Valsts kanceleja», «Ministru prezidents»).
- **Īpašnieks:** operators. Biogrāfiskās atsauces instances (a) pārceltas uz § Junction lomas apgrieztas pārstāstos (agrāk «`subject`» lomai vajag runātāja pierādījumu).

**2026-10-21 (6):** ziņu matcherī paraugs pārbauda VISU doku (`p in text`), lai gan docstring saka «around a name match» — saskaņot docstring vai kodu. Pid 243 izvēlnes paraugi ar to pieņemti apzināti (šodien 0/35 doku ar īstu pieminējumu).

### [OPERATOR] LIELO burtu un handle labojumu atlikumi (2026-10-01)

Kods un pārrēķins — CHANGELOG 2026-10-01 (1)–(2). Verdikti 2026-10-01 B1–B4 izpildīti (`docs/verdikti-2026-10-01.md`): (a) pieņemts, (c) slēgts, (d) Svirskis forma ārā. **Paliek (b) Vēstneša mantotās saites** — 30 rindu izlase (`docs/audits/2026-10-01-vestnesis-saites-izlase.md`): 28/30 pareizi (16 parakstītāji); kļūdas tikai «tikai uzvārda» grupā — 54 no 62 `subject` rindām nav par politiķi (ielas, pagasti, vārdabrāļi), 7 nepārbaudāmas (T19 → `suspect_at`), ~65 no 130 `mentioned` aplami. Filtrs labots 2026-10-01: parakstītāja «I. Uzvārds» un kanoniskais vārds vairs netiek nogriezti. 54 `subject` dzēsti un 7 `suspect_at` 2026-10-01 (`data/rollback_open_questions_2026-10-01.sql`). *Paliek:* 130 `mentioned` «tikai uzvārda» slānī — lasīt pa vienai (T18), ne masveidā. *Īpašnieks:* operators.

### [OPERATOR] Lietuvas «Valsts kontrole» piesaistīta pid 241 (T1, 2026-10-14)

Doc 133481: Lietuvas valsts kontrolieres Segalovičienes paziņojums sasaistīts ar Latvijas Valsts kontroli tikai pēc nosaukuma. Ekstrakcija to atzīmēja tukšu; saite paliek. *Rīcība:* izlemt `negative_patterns` (piem. «Lietuvas Valsts kontrole») — tikai operatora pārskatā; sk. BACKLOG § Ne-darīt (VK prefiksa veto). *Īpašnieks:* operators.
