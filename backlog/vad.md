# BACKLOG tēmas fails

_Sadalīts no `BACKLOG.md` 2026-08-19 — saturs nemainīts. Statusa tagi, uzturēšanas kontrakts un ienākšanas noteikumi: [`../BACKLOG.md`](../BACKLOG.md) preambula. „§ Ne-darīt" un „§ Operatora verdikti" paliek galvenajā failā._

## VAD (declarations)

### [SLĒGTS 2026-08-21] VAD homonīmu kontaminācija 6 politiķiem — DB tīrīta 08-12, live verificēts 08-21, deny-list ieslēgts

**Sanācija piemērota 2026-08-12 (operatora apstiprinājums):** 72 svešās deklarācijas + 505 sekciju rindas dzēstas ar mērķētu DELETE pa adjudikācijas id sarakstu (NE pilnā pid dzēšana + atkalielāde — pid=146 disambig hints principiāli nešķir divus Saeimas deputātus ar vienu vārdu, tāpēc atkalielāde kontamināciju atjaunotu). Pēc-dzēšanas skaiti visiem 6 pid == adjudikācijas PIEDER (24/14/24/5/24/23), 0 bāreņu. Rollback = pilnais snapshot `data/atmina.db.pre-vad-homonimu-purge-20260812` + dzēsto uzskaite `data/rollback_vad_homonimu_purge_2026-08-12.sql`. `vad_disambig` hinti iesēti 5 pid (157, 154, 141, 93, 80) ar programmatiski pārbaudītu separāciju (0 savējo garām, 0 svešo cauri — pret backup svešajām rindām); **pid=146 hints APZINĀTI nav mainīts**.

**Atlikumu izpilde (CHANGELOG 2026-08-21 (5)):**
1. **Deploy — NAV vajadzīgs:** dzīvā vietne verificēta TĪRA 2026-08-21 (6/6 profili, trīs zondes katram: tab skaits == DB, 0 purge-id renderē, 0 dirty-signatūru).
2. **pid=146 aizsardzība — IESLĒGTA:** deny-list (`data/vad_denylist.json` + `src/vad/denylist.py`, vārti pirms disambig un dedup). Stabilā kāja annual/2009+2010 pa (kind, year); interim/end/post_year_* paliek UUID-kāja (best-effort — vad_uuid rotē per-session), tāpēc **pēc katras VAD sweep manuālā pārbaude paliek pastāvīgs tīkls**: ja `[ok] ... skip_denylist=` rindās parādās negaidīti maz trāpījumu pie homonīma meklējuma vai DB pieaug svešas rindas, pārbaudi `vad-denylist-skip` logus un saraksta dzīvīgumu. Saraksta papildināšana tikai ar operatora apstiprinājumu.
3. Parsera robi → atsevišķs ieraksts zemāk (paliek atvērts).

Pilna adjudikācija (visas 186 rindas, ne izlase; identitāti šķīra īpašumu/auto/kapitāldaļu pēctecība + `vad_family` kopas): **114 PIEDER / 72 SVEŠAS / 0 neskaidru** — pid=146 Bērziņš (31/24/7 — kopā TRĪS Andri Bērziņi), pid=157 K. Melnis (32/14/18 — abas "inspektora" plūsmas svešas, pārbaudīts pret NĪ pēctecību), pid=154 Krauze (34/24/10), pid=141 Vīksna (14/5/9 — daļa ir "AIVARS VĪKSNA"), pid=93 Gintere (44/24/20 — Vaiņodes bāriņtiesas persona), pid=80 Bergmanis (31/23/8). Kaskāde: 505 sekciju rindas (159 NĪ, 145 ienākumu, 81 amatu).

**Labojuma ceļš (vēsturisks):** DELETE bez atkalielādes NAV godīgi atritināms (`raw_html` blobi) — nelietot. Rindu saraksts ar pierādījumu katrai: `data/NVO/izpete_2026-08-12/vad_homonimu_adjudikacija.md` (untracked).

### [DAĻĒJI SLĒGTS 2026-08-21] NVO maksājumi × VAD deklarācijas — JOIN atkārtots; parsera robi aizvērti; paliek operatora triāža

Reģ. nr. JOIN starp Valsts kases biedrību maksājumu XLSX un `vad_positions/vad_income/vad_savings/vad_companies` deva 141+24 pārus; triāža + 27 dosjē + spriedumi: `data/NVO/vad_nvo_krustojumi_triaza_2026-08-12.md` un `data/NVO/izpete_2026-08-12/INDEX.md` (untracked).

**Parsera robi AIZVĒRTI 2026-08-21** (CHANGELOG 2026-08-21 (6)): (a) `_REG_NUMBER_RE` paplašināts ar 5-sēriju — 290 positions/229 income/107 companies/28 savings rindas atguva reģ.nr. un pareizo `is_individual`; (b) §13 `<table>` saturs → `other_info` (205 deklarācijām; korektā saucēja ir 205, ne 1285 — vecais skaitlis rādīja virsraksta blokus, ne saturu). Migrācija `scripts/reparse_vad_sections_2026-08-21.py`, rollback `data/rollback_vad_parser_reparse_2026-08-21.sql`. **Pilns re-JOIN izpildīts:** 162 pāras, **24 jaunas** pret 08-12 bāzlīniju — `data/NVO/vad_nvo_rejoin_2026-08-21.md` (NEKOMITĒT klase; t.sk. atgūtais pierādījuma gadījums Vīksna×Junior Achievement 859 647 €). **Paliek [OPERATOR]:** 24 jauno pāru izvērtējums pēc 08-12 triāžas kontrakta (UR/Lursoft pārbaude + oriģinālo deklarāciju pārlase + maksājuma juridiskā daba); publiskā v2 lapa NEietekmēta (reg numuri tur neparādās).
VAD publicēts (`atmina.lv/analizes/vad-2026.html`); plāni `docs/superpowers/plans/archive/2026-05-03-vad-*.md` + `2026-05-05-vad-homonimu-sanacija.md`; triāža `docs/audits/2026-05-05-vad-residual-clusters.md`. Atvērts:
- Algoritmiska izmaiņu pārbaude (2023→2024 lielas summas vs amata maiņa); interešu konfliktu krustpārbaude (`vad_companies` × `saeima_bills.topic`); ārvalstu valūtu→EUR ar ECB gada vidējiem (Dombrava USD 105K); ģimenes uzņēmumu sasaiste ar publisko iepirkumu reģistru.

