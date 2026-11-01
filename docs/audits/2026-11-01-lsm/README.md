# LSM atraduma avotu arhīvs 2026-11-01

Šī mape ir publiskajā spogulī (izņēmums no `docs/audits` izslēguma); `kopijas/` paliek tikai lokāli.

Raksts: `content/analizes/lsm-2026-skaitlos.md`. Pārbaudes gaita: `docs/drafts/lsm-2026/README.md`.

- `archive_lsm.py --copies-only` — katru melnrakstā citēto saiti lejupielādē uz `kopijas/` (`.gitignore`: tikai šajā datorā), raksta `manifest.json` (URL, UTC laiks, HTTP statuss, SHA-256) un `SHA256SUMS`. 2026-11-01: 19 no 19.
- Trīs galveno dokumentu SHA-256 sakrīt ar agrāko lejupielādi tajā pašā dienā: LSM 2025. g. pārskats `da4078…52aa`, SEPLP budžeta izpildes analīze `88ccfa…3eb9`, LSM 2026. g. plāns ar 30.06. grozījumiem (docx) `5dd650…f3b1`.
- X saišu kopijas ir tikai JS čaula bez tvīta teksta. Tvītu teksts glabājas atmina DB `documents` (citēto pozīciju ID — `docs/drafts/lsm-2026/README.md`).
- `dati/` — atvasinātie dati, uz kuriem balstīti TV un portāla skaitļi (publiski, kontrolsummas `SHA256SUMS-dati`): `tv-programmas-2026-09-30--10-27.csv` — LTV1 un LTV7 programma no TV.lv ar mūsu piešķirtajiem žanriem (2066 rindas); `lsm-lv-raksti-2026-09-30--10-27.csv` — LSM.lv rakstu saraksts no sitemap četrās valodās (3739 rindas); `vid-lsm-2026q3.csv` — LSM rinda no VID atvērtajiem datiem par 2026. g. 3. ceturksni.
- Wayback saglabāšana vēl nav veikta. Pēc noteikuma arhivē tikai mediju lapas (LSM, Diena, SEPLP ziņas); Saeimas lapas un «Latvijas Vēstnesis» ir oficiāls reģistrs. Palaist: `archive_lsm.py --spn-only`.
