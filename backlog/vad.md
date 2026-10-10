# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## VAD (declarations)

### [DAĻĒJI SLĒGTS 2026-08-21] NVO maksājumi × VAD deklarācijas — JOIN atkārtots; parsera robi aizvērti; paliek operatora triāža

Reģ. nr. JOIN starp Valsts kases biedrību maksājumu XLSX un `vad_positions/vad_income/vad_savings/vad_companies` deva 141+24 pārus; triāža + 27 dosjē + spriedumi: `data/NVO/vad_nvo_krustojumi_triaza_2026-08-12.md` un `data/NVO/izpete_2026-08-12/INDEX.md` (untracked).

**Parsera robi AIZVĒRTI 2026-08-21** (CHANGELOG 2026-08-21 (6)): (a) `_REG_NUMBER_RE` paplašināts ar 5-sēriju — 290 positions/229 income/107 companies/28 savings rindas atguva reģ.nr. un pareizo `is_individual`; (b) §13 `<table>` saturs → `other_info` (205 deklarācijām; korektā saucēja ir 205, ne 1285 — vecais skaitlis rādīja virsraksta blokus, ne saturu). Migrācija `scripts/reparse_vad_sections_2026-08-21.py`, rollback `data/rollback_vad_parser_reparse_2026-08-21.sql`. **Pilns re-JOIN izpildīts:** 162 pāras, **24 jaunas** pret 08-12 bāzlīniju — `data/NVO/vad_nvo_rejoin_2026-08-21.md` (NEKOMITĒT klase; t.sk. atgūtais pierādījuma gadījums Vīksna×Junior Achievement 859 647 €). **Paliek [OPERATOR], ATLIKTS 2026-09-07** (verdikts 52): 24 jauno pāru izvērtējums pēc 08-12 triāžas kontrakta (UR/Lursoft pārbaude + oriģinālo deklarāciju pārlase + maksājuma juridiskā daba). **Atbloķētājs ir UR izraksti** — triāžas kontrakts tos prasa, un bez tiem sesija apstātos pirmajā pārī. Publiskā v2 lapa NEietekmēta (reģ. numuri tur neparādās).
VAD publicēts (`atmina.lv/analizes/vad-2026.html`); plāni `docs/superpowers/plans/archive/2026-05-03-vad-*.md` + `2026-05-05-vad-homonimu-sanacija.md`; triāža `docs/audits/2026-05-05-vad-residual-clusters.md` — **fails vairs neeksistē** (`docs/audits/` bija gitignorēts līdz 2026-08-22, tāpēc pirms tam citētie audita dokumenti ir zuduši; mapē agrākais saglabājies ir 2026-08-19). Šo triāžu nevar pārlasīt — ja tās secinājumi vajadzīgi, tie jāatvasina no jauna. Atvērts:
- Algoritmiska izmaiņu pārbaude (2023→2024 lielas summas vs amata maiņa); interešu konfliktu krustpārbaude (`vad_companies` × `saeima_bills.topic`); ārvalstu valūtu→EUR ar ECB gada vidējiem (Dombrava USD 105K); ģimenes uzņēmumu sasaiste ar publisko iepirkumu reģistru.

### [SLĒGTS 2026-10-08] VAD resweep: 53 ielādētas, 113 vārdabrāļi bloķēti, 2 izņemti, 2 atjaunoti

**Izdarīts 2026-10-08** (CHANGELOG 2026-10-08 (12)). Dry-run «166 jaunās / 46 pid» NEBIJA iztrūkstošas deklarācijas: **101 no 166** bija jau agrāk izņemtas vārdabrāļu rindas — denylist uuid kājas klusi zaudēja spēku (VID rotē uuid). Labots ar identitātes kāju (`src/vad/denylist.py`, `d028a392`). Triāža (3 Opus palīgi, publiskā karjera; `docs/audits/2026-10-08-vad-resweep-triaza/verdicts_{A,B,C}.md`): 38 REAL, 113 vārdabrāļi (101 agrāk + Bērziņš 7 + 5 jauni), 15 UNCLEAR. Atkārtots dry-run visiem 45 pid: `new=38`, 0 kļūdu. Ielāde `--pids` 28 politiķiem: `new=38`, kopā 2783 → 2821 → 2822 pēc Zīles/Elksniņa (rollback `data/rollback_vad_resweep_load_2026-10-08.sql`, snapshot `.scratch/atmina.pre-vad-resweep-20261008.db`). `audit_vad_profile_match` [OK].

**Neskaidrās izšķirtas 2026-10-08** (CHANGELOG (13)) pēc ģimenes/amatu paraksta no VID detaļām: Jenzis 14 + Žuravļevs 1 ielādēti; Burovs 2 — svešs (paliek denylist); Elksniņš 2 atjaunoti; Zīle 3053 un Ijabs 1838 izņemti; Zemmers, Ijabs «Senators», Bērziņš 2006–2011 — paša. Kopā 2836.

**Paliek (process, ne darbs):** nākamā gada vārdabrāļa annual identitātes kāja NEnoķer (jauna etiķete) — mēneša dry-run triāža obligāta (`operacijas.md` § VID); ģimenes paraksta rīks `scripts/vad_peek.py --pids`.

### [DEFERRED] VAD: `_norm_kind` «stājoties amatā» / «Beidzot darbu» → `interim`; kartējums dublēts

`declaration_kind` ir `interim` 204/2 783 prod rindām, kuru etiķete ir «… stājoties amatā …» vai «Beidzot darbu …» (vaicājums: `declaration_kind='interim' AND (declaration_type LIKE '%stājoties amatā%' OR … '%Beidzot darbu%')`, 2026-10-08). Attēlošanai nekaitē — renders lasa etiķetes tekstu, ne `kind`; dedup vairs nelieto `kind` (tikai `deny_hit`). Kartējums dublēts: `src/vad/parsing.py::_norm_kind` un `src/vad/declarations.py::_norm_kind_from_label`. *Trigeris:* pirmais patērētājs, kas filtrē pēc `declaration_kind` (`start`/`end`). *Rīcība:* viena funkcija abiem + datu migrācija ar rollback. *Īpašnieks:* kods.
