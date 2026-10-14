# Nodošana: operatora verdiktu izpilde (52 lēmumi) — jaunai sesijai

> ## Statuss: IZPILDĪTS 2026-09-07 — sk. CHANGELOG (1)–(9)
>
> Šis dokuments ir **izpildīts un slēgts**. Patiesības avots par to, kas nostrādāja dzīvē, ir `wiki/CHANGELOG.md` ieraksti `## 2026-09-07 (1)`–`(9)`; per-rindas statuss — [`verdikti-2026-09-06.md`](verdikti-2026-09-06.md) (katrai rindai «Statuss 2026-09-07» aiz ieteikuma).
>
> **Iznākums:** 31 rinda izpildīta, 5 NESAKRĪT (mērījums apgāza verdikta pamatojumu — 7, 10, 19, 35, 37), 1 nav izpildīta pretrunas dēļ (29 — Toro = Gobzems, 2026-09-05 (4) operatora fakts), 2 sagatavotas operatora apstiprinājumam (31, 34), 13 atliktas vai NĒ pēc paša ieteikuma. Backlog attīrīts tajā pašā sesijā: 11 ieraksti izgriezti, 13 pārrakstīti, 2 jauni; `BACKLOG.md` + `backlog/*.md` 1 024 → 865 rindas.
>
> **Rūtiņas zemāk atzīmētas pēc faktiem**, ne pēc nodoma: `[x]` = izpildīts vai apzināti un pierakstīti atlikts, `[ ]` = neizpildīts (sagatavots un gaida operatoru, vai atcelts ar mērījumu), ar iemeslu rindā.

Sagatavots 2026-09-06 vakarā. **Operatora lēmums 2026-09-06 (burtiski): «vari visiem darīt kā rekomendēts bet jaunā sesijā».** Tātad katrai rindai `docs/verdikti-2026-09-06.md` izpildāms tās **Ieteikums** bez atkārtotas jautāšanas — izņemot vietas, kur ieteikums pats saka ATLIKT vai prasa operatora skatu pēc lasīšanas (norādīts zemāk).

Pirms darba lasīt: `CLAUDE.md` (T2, T6, T14, § Escalation 8 — rollback + re-embed), `docs/verdikti-2026-09-06.md` pilnībā (52 rindas + § Kas notiek pēc atbildēm), `BACKLOG.md` § Ne-darīt.

## Kārtība un robežas

Darīt **grupu pa grupai, katrai savs commit**; nekad batch-UPDATE pār vairākiem pid vai claim bez per-rindas rollback. Katra datu mutācija: `data/fix_<scope>_2026-09-07.sql` + `data/rollback_<scope>_2026-09-07.sql` pāris ar unikālu scope sufiksu, komitēti PIRMS izpildes. `topic`/`stance` maiņa → `scripts/reembed_claims.py <id>` un vektora maiņas pārbaude. Rezolūcijas marķieris `Izvērtēts 2026-09-07:` AIZVIETO `NEEDS_REVIEW: `; kolonnu `review_status` ar roku neraksta; rezolūcijas tekstā karoga vārdu nemin.

Pēc katras grupas: CHANGELOG rinda ar datumu, verdikta rindas izgriešana no `BACKLOG.md` / `backlog/*.md` (indeksa skaitļi — `tests/test_backlog_index_sync.py`). Publicētos pārskatus NEpārraksta.

Vēlēšanu sezona — prioritāte datu integritātei (A, B, D30, E36–38), UI pēdējais.

## To-do (secībā)

### 1. Izgriezt jau slēgto (bez lēmuma)
- [x] Rindas 53–57: #689736 verdikts, Lindbergas teikums, `x_handle IS NULL` klase (+ salabot tukšo atsauci `dati-db.md § x_handle IS NULL`), `matcher.md` tukšā atsauce «§ pid=234 Arigo Toro», Ceriņa svītrotā rinda.

### 2. Grupa A — per-rindas dati (10 rindas, ~1 h)
- [x] 1: atsaukt #689743 un #689646 (Sprūds). Izlemt un pierakstīt, vai avota tvīti paliek profila X cilnē (paliek — tie ir viņa publiskie posti).
- [x] 3: #704121 `topic` → `Korupcija un KNAB`; kolīzija pārbaudīta 09-06 (0), pārbaudīt vēlreiz pirms izpildes; re-embed.
- [ ] 7: **NESAKRĪT** — doc 91765 katru stances daļu piedēvē Mieriņai («Vienlaikus viņa uzsvēra…» seko tieši aiz «Mieriņa norādīja»), tāpēc nav ko sašaurināt. DB nemainīts.
- [x] 8: #521109 (Krusts) — paplašināt stanci pēc avota; re-embed.
- [x] 9: atsaukt #703870 (Braže, pašas RT).
- [ ] 10: **NESAKRĪT** — citāts doc 80022 IR: 251 no 252 zīmēm sakrīt zīme zīmē, atšķiras vienīgi noslēguma pieturzīme. Tā ir pieturzīmju klase (50. rinda), ne pārskrāpējums; `quote` saglabāts, `reasoning` NAV papildināts — tas ierakstītu korpusā nepatiesu apgalvojumu.
- [x] 2, 4, 5, 6: NĒ — tikai izgriezt verdikta rindas.

### 3. Grupa B — partija / amats / aktivitāte (T6)
- [x] 12: Melbārde `role` → ĀM parlamentārā sekretāre (avoti 08-25 doki); `party` NEmainīt.
- [x] 13: Štekerhofs `relationship_type` → `tracked` (514 balsojumi, pēdējais 03.09.); pēc tam doki 90283, 89625 atgriežas rindā — apzināti.
- [x] 15: Labanovskis `role` → Smiltenes novada domes priekšsēdētājs (pārbaudīt pašvaldības lapā); reaktivāciju neveikt.
- [x] 16: Ruģēns `role` → NULL. 17: Aizupietis NULL pieņemts — izgriezt.
- [x] 18: Kronbergs — 10 no 27 `subject` dokiem izlasīti, **10 no 10 ir par DB Kronbergu**; identitātes sajaukšanas hipotēze atspēkota, `role` nemainīts, ieraksts izgriezts no `backlog/matcher.md`.
- [ ] 19: **NESAKRĪT — slēgts pa «apstiprināt» zaru.** 2026-07-16 operatora lēmums abas rindas jau atzina par leģitīmām; `/audit-integrity` 2. pārbaudes (c) zars nefiltrē `active`, tāpēc karogs nepazustu; `src/social.py` fetch filtrē `active = TRUE`, tāpēc deaktivēšana apturētu dzīvu kanālu (1 689 doki, satura pārklāšanās ar `@ESvirskis` = 0). Ierakstīts `BACKLOG.md` § Ne-darīt kā dokumentēts izņēmums.
- [x] 11, 14: **ATLIKTS, atbloķētājs pierakstīts** — 11 gaida Rēzeknes pašvaldības vai CVK avotu (`backlog/avoti.md`), 14 gaida CVK saraksta verifikāciju; doc 89625 liecina par apcietinājumu (`backlog/dati-db.md`).

### 4. Grupa C — konvencijas (teksts nesējos, ne DB)
- [x] 20: `claim-extractor.md` Step 4 — `stated_at` = publiskošanas diena, ja izteikuma diena ārpus 7 d loga; vēsturiskās NEbīda.
- [x] 21: atsaukt #704024 (Dombrovska apsveikums) — vienīgā DB darbība grupā.
- [x] 22: #704165 `topic` → `Aizsardzība un drošība`; re-embed.
- [x] 23: Māsas balsojumu konvencija — `generate_claims_from_votes` docstring + `saeima-tracker.md` Step 3.5.
- [x] 24: `/audit-integrity` jauna pārbaude: ne-kanonisko `position` tēmu skaits (bāzlīnija 0/33). Kodu `db.store_claim` NEmainīt.
- [x] 25: `@quality-reviewer` § C2 rinda par spriedžu/piezīmju laika apgalvojumiem (viens teikums).
- [x] 26: confidence-drift detektors rāda n abās pusēs, klusē n<5; tests.

### 5. Grupa D — sēšana un formas (visi caur `/seed-entity` un eval vārtiem)
- [x] **30 (prioritāte):** Meļņi. Izlasīt 25 dokus (pid=157 junction + «aizsardzības ministr» bez «Kaspars»); katrai no 54 pid=157 pozīcijām, kas nāk no tiem, pārbaudīt, vai runātājs ir Raivis (pid=224). Pāratribūcija = `opponent_id` UPDATE ar rollback + re-embed. `negative_patterns` kailajai formai tikai caur `scripts/eval_matcher_collisions.py` (FP≤3, zelts≥1260). Ja skartas publicētas pozīcijas — pierakstīt, kuras.
- [ ] 34: **SAGATAVOTS, gaida operatoru** — `data/proposed_name_forms_2026-09-07.md` (17 rindas). **Pamatojums nesakrita:** tukšas `name_forms` NEnozīmē trūkstošus locījumus (matcher tos ģenerē pats) — trūkst tikai ASCII variantu, un tie 89 649 doku korpusā ir vērti **5 dokumentus**; 61 no 66 ierosinātajām formām nedod nevienu trāpījumu.
- [ ] 35: **NESAKRĪT — `relay` NEIETEIKTS.** RT tiešām ir 211 no 237 `subject` dokiem, bet **visas 28 pozīcijas nāk no viņa paša tvītiem**, un `relay` tās nogrieztu. RT troksnis pieder 36.–38. rindas mehānismam.
- [x] 27, 28: sēt Pujātu un Freifaltu (`/seed-entity`, ar rollback).
- [ ] 29: **NAV IZPILDĪTS — pretrunā ar 2026-09-05 (4) operatora faktu.** Toro IR pārdēvētais Aldis Gobzems, tāpēc `Gobzem*` ir viņa paša vārda formas un PALIEK. Verdikta premisa («saraksta nosaukums, ne viņa vārds») ir nepareiza. Stop beats write.
- [ ] 31: **SAGATAVOTS, gaida operatoru** — `data/fix_grupaD_zile_negative_patterns_2026-09-07.sql` + pāra rollback; 41 doks korpusā, 0 ar īstu Roberta Zīles vārda formu, 2 nepatiesas junction rindas; eval vārti abās pusēs vienādi (`fp_links=1`, zelts 97,93 %).
- [x] 33: Valainis vārdabrālis — NEatsevišķi; pierakstīt kā konteksta kolokācijas dizaina uzdevumu kopā ar 30 (`backlog/matcher.md`).
- [x] 32: **ATLIKTS** — viena instance nepamato eval vārtu palaidienu; pārmērīt, ja parādās otra.

### 6. Grupa E — kods (tests, kas krīt pirms labojuma)
- [x] 36+37+38: `organization|relay` slotiem un @Brivibas36 → pid=10 neģenerēt `role='subject'` (`src/matcher.py` / `link_politicians_to_documents`); tests; pēc tam `eval_matcher_collisions.py`; pārmērīt nepārskatīto rindu (bija 6 493, no tiem LETA 934, NBS 38).
- [x] 39: Vēstnesis — sk. § Vēstnesis zemāk. Vārts rutīnas statusā: dienā ar `platform='vestnesis'` doku, kura virsraksts sākas ar «Ministru kabineta» / «Saeimas» / «Valsts prezidenta», uzrādīt to orkestratoram (ne rindā). Nepatiesais komentārs `src/analyze.py:167-172` un `src/scope.py` jāpārraksta ar faktiem.
- [x] 40: nogrieztā ievada vārts — karogo (`documents` atzīme vai log), ne atmet; saucējs atskaitē.
- [x] 41: avota etiķete no `documents.source_domain` visās claim virsmām (profili, tēmas `topics.py:164`, pārskati); `check.sh` + `--only=politiki,temas`; deploy `--no-delete`.
- [x] 42: `/audit-integrity` 9. pārbaude — atsevišķs saucējs «ministri bez balsojumu seguma».
- [x] 44: `claims.review_status_at` kolonna, ko uztur esošais trigeris; migrācija + rollback + tests.
- [x] 47b: viena audita rinda `generate_image()` līmenī (prompt, modelis, cena, kind); `cli thread --style light|sepia`.
- [x] 48: X pūla pārmērījums (`get_pool().status()`), tad lēmums par `search`.
- [x] 49b: `src/csp/` sync pieslēgt (lēmums 08-15).
- [x] 43, 45, 46, 47a, 49a, 49c: ATLIKT/NĒ — izgriezt vai pārrakstīt statusu.

### 7. Grupa F — atsevišķas sesijas (katra savā)
- [ ] 50: **ATLIKTS — sesija NAV palaista.** Apjoms precizēts: 13 `paraphrase_mid` + 179 pieturzīmes + 37 vājie + 17. pārbaudes 7 jaunie id (615955, 689768, 704089, 704179, 704217, 704342, 709073). **615955 ir pieturzīmju klase, ne pārskrāpējums** (sk. 10).
- [ ] 51: **ATLIKTS — sesija NAV palaista.** `platform='video'` doku skaits joprojām 0; Kola LTV intervija paliek pirmais kandidāts, Briškena debašu video NĒ.
- [x] 52: **ATLIKTS** — gaida UR izrakstus; bez tiem triāža apstātos pirmajā pārī.

### 8. Noslēgums
- [x] `bash scripts/check.sh` — pēdējais pilnais palaidiens: ruff zaļš, **2 538 testi passed**, renders zaļš, `check_output` tīrs. `/audit-integrity` palaista DAĻĒJI: 2., 4., 6., 8., 9b., 13., 17. un 18. pārbaudei jaunas bāzlīnijas; **1., 1b. un 12. pārbaude (matcher pārlaidieni pār korpusu) NAV palaistas — tas nav tīrs rezultāts, tikai nemērīts.**
- [x] CHANGELOG ieraksti `## 2026-09-07 (1)`–`(9)` — deviņi bloki, katrs ar mērījumiem un ar to, **kas labojumu izpildīja dzīvē** (tests, korpusa skrējiens vai palaidiens).
- [x] `docs/verdikti-2026-09-06.md` galvā statusa bloks ar CHANGELOG karti + katrai rindai «Statuss 2026-09-07»; `BACKLOG.md` un `backlog/*.md` attīrīti tajā pašā piegājienā.

## Vēstnesis — fakti 2026-09-06 (rindai 39)

- `platform='vestnesis'`: **2 149 doki** (30.04.–04.09.), no tiem 225 ar `reviewed_at` (30.04.–01.09.), **11 claims** kopā (pēdējais #704343 01.09. Rinkēvičs; pārējie maijs–aprīlis). Junction: 905 `subject`, 2 186 `mentioned`.
- Ekstrakcijas rindā tie NAV kopš 2026-05-06 (`src/analyze.py:194`, `:265`): SA-3 partija atrada 24/33 dokus kā procedurālus ministru parakstus. Tie nonāk `wiki/log-ingest` un pārskata «Šodien izsludināts» caur junction.
- Saturs: lielākā daļa ir sludinājumu klases (izsoles, mantojumi, UR ziņas, tiesu uzaicinājumi — 12 lielākās klases ≈ 800 doku); **466 doku virsrakstā ir MK / Saeima / rīkojums / likums**. Piemērs, kas maksāja: doc 95670 «Ministru kabineta krīzes vadības sēdes protokols» (26.08.) ar septiņiem valdības termiņiem — `reviewed_at IS NULL`, neviens to nelasīja.
- Secinājums rindai 39: izslēgšana no rindas ir pareiza sludinājumiem, bet 466 MK/Saeimas doki ir cita klase. Vārts (variants b) tos uzrāda; ja pēc mēneša uzrādīto skaits ir stabils un mazs (<5/dienā), var apsvērt tiešu ievilkšanu rindā ar virsraksta filtru.

## Kas šajā sesijā (2026-09-06) jau izdarīts — nedublēt

Tēmu lapas A1–A5 (`2b48c541`), airBaltic 1. daļas labojums + 2. daļa publicēta ar abiem hero (`8a82c5ae`, attēli serverī), `@quality-reviewer` § H valodas vārti, `quality-bars` § Sintēze, Nozīmīgums → vārds (`f9f9c3e2`, deploy ar nākamo rutīnu), soc. teksti (X, r/atminaLV, FB) sagatavoti, backlog +2 ieraksti, verdiktu saraksts (`57a3c623`). Nākamajā rutīnas deploy līdzi aiziet: Nozīmīguma vārdi, 2. daļas divi teikumi, profilu sintēžu sīktēli.
