# Handoff 2026-10-01 — vakara dienas rutīna (PABEIGTA, publicēta)

> **Statuss:** rutīna 10/11 ✓ (4. solis — nebija pretrunu). Deploy 23:03 `c9acd401`, `verify_host` 9/9, attēlu URL 4/4 = 200.

## Kas izdarīts (21:20–23:10)

- **Ielāde** 21:24–21:43, 5/5 OK: 898 doki (web 135, X 448 + mentions 249, Vēstnesis 66). TypeSafe ēna: judged 170, vetoed 2 (abi Jātnieks izsoles sludinājumā — pareizi) → diena skaitās ēnas nedēļā, 0 zelta zaudējumu.
- **Saeima 01.10** (`@saeima-tracker`): 57/57 balsojumi (#8323–#8379; 24.09 turpinājums 26 + kārtējā 22 + 9 apakšpunkti `getTechDKP`), `politician_id IS NULL` 0/4896, summary 51/0. Divi summary labojumi + 79/85 stance — `data/rollback_saeima_summaries_2026-10-01.sql`. Manifests pārģenerēts; paritāte 09-24 37/0.
- **Ekstrakcija:** plāns 32 aģenti / 256 pāri → apstrādāti 256/256 (#32 apstājās pie 12 dokiem, atlikumu 6 izdarīja #32b). Atgūšana 22+1 pāri → 11 pozīcijas. Kopā **84 pozīcijas** (729656–729739, 53 politiķi), 26 NEEDS_REVIEW; DB skaits = aģentu atskaišu summa.
- **Pretrunas:** 0 (`@contradiction-hunter`, 84 pozīcijas, 57 balsojumi, 12 noraidīti kandidāti `logs` #655815).
- **Spriedzes** #418–#422 (4 no 11 TypeSafe priekšlikumiem + Kols→Braže ar roku). **Tendences** #665–#668. **Pārskats** #669, attēls #354 (A; #355 noraidīts).
- **Labojumi ar rollback:** `rollback_stance_rutina` (729724 vērtējums ≠ fakts, 729664, 729730), `rollback_<uzvārds>_anon` (sk. zemāk), `rollback_qr` (quality-reviewer 6 labojumi), `rollback_velps_729660` (atruna «esot»/«iespējamo»). Visi re-embed izdarīti.
- `check.sh` zaļš pēc likumu bāzlīnijas REGEN (`render_baseline_laws.json`, 6 lapas pēc wiki sync).

## Operatoram izlemt / ratificēt

- **Redakcionāls lēmums (ratificē vai atsauc):** bijušā Progresīvo biedra uzvārds izņemts no MŪSU stance tekstiem (729664, 729696, 729728) un pārskata #669 — apsūdzība par noziegumu pret nepilngadīgo, nav celta. Citāti netika mainīti. **Nav notīrīts:** paši tvīti `documents` 121412 (Liepnieks) un 121286 (Stendzenieks) satur uzvārdu un rādās šo politiķu profilu X cilnē (viņu pašu publiskie vārdi, ne mūsu atstāsts). Atsaukšana: `data/rollback_<uzvārds>_anon_2026-10-01.sql` + re-embed.
- ~~**T6:** Uzulnieks~~ — IZDARĪTS 23:15 (operators): `party` → «Bezpartejisks», rollback `data/rollback_uzulnieks_party_2026-10-01.sql`, deploy `07fb60c5` (verify_host 9/9). Bijušais Progresīvo deputāts nav `tracked_politicians` — nav ko mainīt.
- **Saeima:** 01.10 dzīvajai sēdei vēl nav `nr={UUID}` → paritātes audits rīt (`audit_saeima_agenda_parity.py --dates 2026-10-01`, manifests jāpārģenerē). Avoti `.playwright-mcp/saeima-2026-10-01/`. Ap 12 punktiem palika nebalsoti — gaidāms turpinājums.
- **Siliņa / sporta fonds (1380/Lp14):** pārbaudīt pret 01.10 stenogrammu (~10 d), vai JV atmeta savu 3 % priekšlikumu (`rejected_candidates` #655815).
- **Vēstneša filtra pirmā dzīvā ielāde:** 66 doki, 48 piesaistīti, 80 junction rindas (Kulbergs subject 27, Rinkēvičs 17). Inversija: doc 121897 Latvijas Banka `subject`, Rinkēvičs `mentioned`.
- **BACKLOG kandidāti:** (a) `src/quality.py` garumzīmju vārti noraidīja pareizu īsu LV teikumu bez garumzīmēm (pid 167 `analyses` rinda; atjaunota ar garāku tekstu, #11270); (b) `test_likumi_detail_pages_byte_identical` nav hermētisks — fikstūras DB, bet lasa dzīvos `wiki/laws/*.md`, tāpēc krīt pēc katras Saeimas sēdes wiki sync (REGEN 09-18, 09-25, 09-28, 10-01).
- **Iepriekšējie atvērtie:** publiskais spogulis vēl `c7e6eda`; DMARC `p=quarantine` pēc 09-30 — abi operatora soļi.
