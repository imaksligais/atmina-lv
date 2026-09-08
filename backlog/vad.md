# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Atliktais pēc 2026-09-06 verdiktiem" (agrāk „§ Operatora verdikti") paliek galvenajā failā._

## VAD (declarations)

### [DAĻĒJI SLĒGTS 2026-08-21] NVO maksājumi × VAD deklarācijas — JOIN atkārtots; parsera robi aizvērti; paliek operatora triāža

Reģ. nr. JOIN starp Valsts kases biedrību maksājumu XLSX un `vad_positions/vad_income/vad_savings/vad_companies` deva 141+24 pārus; triāža + 27 dosjē + spriedumi: `data/NVO/vad_nvo_krustojumi_triaza_2026-08-12.md` un `data/NVO/izpete_2026-08-12/INDEX.md` (untracked).

**Parsera robi AIZVĒRTI 2026-08-21** (CHANGELOG 2026-08-21 (6)): (a) `_REG_NUMBER_RE` paplašināts ar 5-sēriju — 290 positions/229 income/107 companies/28 savings rindas atguva reģ.nr. un pareizo `is_individual`; (b) §13 `<table>` saturs → `other_info` (205 deklarācijām; korektā saucēja ir 205, ne 1285 — vecais skaitlis rādīja virsraksta blokus, ne saturu). Migrācija `scripts/reparse_vad_sections_2026-08-21.py`, rollback `data/rollback_vad_parser_reparse_2026-08-21.sql`. **Pilns re-JOIN izpildīts:** 162 pāras, **24 jaunas** pret 08-12 bāzlīniju — `data/NVO/vad_nvo_rejoin_2026-08-21.md` (NEKOMITĒT klase; t.sk. atgūtais pierādījuma gadījums Vīksna×Junior Achievement 859 647 €). **Paliek [OPERATOR], ATLIKTS 2026-09-07** (verdikts 52): 24 jauno pāru izvērtējums pēc 08-12 triāžas kontrakta (UR/Lursoft pārbaude + oriģinālo deklarāciju pārlase + maksājuma juridiskā daba). **Atbloķētājs ir UR izraksti** — triāžas kontrakts tos prasa, un bez tiem sesija apstātos pirmajā pārī. Publiskā v2 lapa NEietekmēta (reģ. numuri tur neparādās).
VAD publicēts (`atmina.lv/analizes/vad-2026.html`); plāni `docs/superpowers/plans/archive/2026-05-03-vad-*.md` + `2026-05-05-vad-homonimu-sanacija.md`; triāža `docs/audits/2026-05-05-vad-residual-clusters.md` — **fails vairs neeksistē** (`docs/audits/` bija gitignorēts līdz 2026-08-22, tāpēc pirms tam citētie audita dokumenti ir zuduši; mapē agrākais saglabājies ir 2026-08-19). Šo triāžu nevar pārlasīt — ja tās secinājumi vajadzīgi, tie jāatvasina no jauna. Atvērts:
- Algoritmiska izmaiņu pārbaude (2023→2024 lielas summas vs amata maiņa); interešu konfliktu krustpārbaude (`vad_companies` × `saeima_bills.topic`); ārvalstu valūtu→EUR ar ECB gada vidējiem (Dombrava USD 105K); ģimenes uzņēmumu sasaiste ar publisko iepirkumu reģistru.

