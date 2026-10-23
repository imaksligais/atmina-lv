# DB momentuzņēmumu retention

> **Statuss: SPĒKĀ — operatora apstiprinājums 2026-08-05.** Pirmā izpilde tajā
> pašā dienā: 18 faili / 5,90 GB dzēsti pēc zemāk esošās tabulas (pieraksts
> CHANGELOG § 2026-08-05); paliek 11 faili — dzīvā DB ar blakusfailiem,
> 4 momentuzņēmumi ≤60 d, pierādījuma trio un `csp.db`.

## Konteksts

`data/atmina.db.pre-*` / `atmina_backup_*` momentuzņēmumi ir pirms-migrāciju
atjaunošanas punkti. Tie ir gitignorēti (tikai lokāli), tāpēc nekādu publiskā
spoguļa risku nerada — izmaksa ir disks un neskaidrība, kurš vēl ir jēgpilns
atjaunošanas punkts. Primārais atcelšanas ceļš vienmēr ir pāra
`data/rollback_*.sql`; momentuzņēmums ir drošības josta gadījumam, kad
rollback pats izrādās kļūdains (tā 2026-08-03 tika rekonstruētas divas
pirms-attēlu kopas).

**Inventārs 2026-08-05** (vaicājums: `Path("data").glob("*.db*")` + `stat`):
29 faili, 15,6 GB kopā — dzīvā DB 2,18 GB, WAL/SHM blakusfaili ~0, `csp.db`
0,2 MB (atsevišķs BACKLOG § Repo higiēna lēmums), un **23 momentuzņēmumi
~13,2 GB** (2026-04-19 → 2026-08-02).

## Noteikums

1. **Glabā 60 dienas no izveides.** Pēc 60 dienām momentuzņēmums vairs nav
   reālistisks atjaunošanas punkts — DB kopš tā ir mainījusies par tūkstošiem
   rindu, un atgriešanās notiktu pa rollback failiem, ne pa pilnu kopiju.
2. **Mūžīgi glabā pierādījuma momentuzņēmumus** — failus, kas vārdiski citēti
   BACKLOG / CHANGELOG / Ne-darīt kā izmeklējuma pierādījums. Šobrīd divi,
   abi kopš 2026-08-14 dzīvo `data/backups/` (WAL konsolidēts, astes noņemtas):
   `atmina.db.pre-vote-url-fix-20260427-154228.backup` — izšķirošais pierādījums
   `store_claim()` idempotences izmeklējumā (BACKLOG § Ne-darīt) — un
   `atmina.db.pre-vad-homonimu-purge-20260812` (VAD homonīmu sanācijas
   rollback avots). Pirms jebkuras dzēšanas grep nosaukumu pa repo.
3. **Dzēšana tikai ar operatora apstiprinājumu**, uzskaitot konkrētos failus
   un GB; izpildīto dzēšanu pieraksta commit ziņā (faili ir untracked, tāpēc
   diff to neparādīs — commit teksts ir vienīgā pēda). CHANGELOG ieraksts
   pienākas tikai tad, ja mainās pati glabāšanas konvencija.
4. **Jauna momentuzņēmuma vārdā vienmēr ir datums** (`YYYYMMDD` vai
   `YYYY-MM-DD`) — bezdatuma formas (`pre_matcher_fix`) padara 1. punktu
   nepiemērojamu bez `stat`.

## Verdikti pēc noteikuma (2026-08-05 stāvoklis; DZĒŠAMS rinda izpildīta tajā pašā dienā)

| Verdikts | Faili | Apjoms |
|---|---|---|
| PALIEK (dzīvā DB + WAL/SHM) | `atmina.db` + 2 blakusfaili | 2,18 GB |
| PALIEK (≤60 d) | `pre-dup-cleanup-20260802`, `pre-registration-claims-purge-20260725`, `pre-krisjanis-purge-20260613`, `pre-klavins-reseed-20260613` | 7,4 GB |
| PALIEK (pierādījums, 2. punkts) | `pre-vote-url-fix-20260427-154228.backup` (+wal/shm) | 0,13 GB |
| **DZĒŠAMS pēc apstiprinājuma (>60 d)** | 18 faili: `pre-summary-backfill-20260603`, `pre-klavins-reattribution-20260531`, `pre-vitenbergs-retrofetch-20260526`, 3× maija `backup-2026-05-*`, `pre-vad-phase2-2026-05-05`, 2× `pre-x-backfill-2026-04-30`, `pre_title_backfill_20260430`, `pre-video-smoke`, `pre-refactor-20260429`, 2× `pre-phase-1c-*`, `pre-bills-backfill-20260427`, `pre_saeima_doc_cleanup_2026-04-25`, `pre_external_profiles`, `pre_matcher_fix` | **~5,9 GB** |

(06-13 pāris noteikumam izies 2026-08-12, 07-25 — 09-23; tad dzēšamā aste
pieaug līdz ~11 GB.)

## 2026-08-14 stāvoklis (tīrīšanas plāna izpilde)

- Abi pierādījuma momentuzņēmumi (2. punkts) konsolidēti `data/backups/` —
  WAL checkpoint + astes noņemtas; `data/backups/` satur TIKAI tos divus
  (+ divi mazi ne-DB audita artefakti, atsaukti no arhivēta 04-25 plāna).
- 12 vēsturiskie `data/backups/` momentuzņēmumi (4,2 GB, 04-22 … 05-25, visi
  >60 d, neviens nav pierādījuma klase) pārvietoti uz auksto arhīvu
  `E:/atmina-arhivs/2026-08/db-backups/` — saraksts CHANGELOG 2026-08-14.
- `data/` saknē paliek 4 momentuzņēmumi pēc šīs lapas 1. punkta:
  `pre-dup-cleanup-20260802` un `pre-registration-claims-purge-20260725`
  (≤60 d, paliek) un **06-13 pāris (`pre-klavins-reseed`, `pre-krisjanis-purge`,
  ~3,4 GB), kam 60 dienu termiņš beidzās 2026-08-12 — dzēšams pēc 3. punkta
  operatora apstiprinājuma**. _Atjauninājums 2026-08-21: pāris tika dzēsts JAU
  2026-08-14 ar operatora tiešu apstiprinājumu (CHANGELOG «Papildinājums» tajā
  dienā, 3,42 GB) — šī rinda palika nestāvoklī; `data/` saknē tagad ir tikai
  dzīvā DB, `csp.db`, abas ≤60 d kopijas un pierādījuma trio `data/backups/`._
- Inventāra vaicājuma piezīme: `Path("data").glob("*.db*")` NAV rekursīvs —
  pilnam inventāram jāskrien arī `Path("data/backups").glob("*")`.

## Ārējā kopija (reizi nedēļā)

**Kas.** `scripts/backup_db.py` reizi nedēļā izveido šifrētu un pārbaudītu
`data/atmina.db` un `data/csp.db` kopiju ārpus E: diska. Atšķirībā no
momentuzņēmumiem augstāk šī kopija sargā pret diska nāvi, ne tikai pret kļūdainu
migrāciju. `data/jev_cache.db` netiek kopēts — tā ir atjaunojama kešatmiņa.

**Kur.** Galamērķi nosaka gitignorētais `.env.backup` (paraugs
`.env.backup.example`). Noklusējums ir `local:D:/atmina-backups` — atsevišķs
fizisks disks šajā datorā. Tas sargā pret E: diska kļūmi, bet **NE pret visa
datora zudumu** (zādzība, ugunsgrēks, barošanas bloka bojājums). Kopija ārpus šī
datora (`ssh:<alias>:<mape>`) joprojām ir atvērts darbs. Skripts atsaka
galamērķi repo kokā un attālo mapi ar `public_html`.

**Kā palaist** (iknedēļas rutīnas solis):

```bash
.venv/Scripts/python.exe scripts/backup_db.py --dry-run   # plāns, neko nedara
.venv/Scripts/python.exe scripts/backup_db.py             # kopija
```

Izejas kods 0 = kopija gatava un pārbaudīta; 1 = kļūda, nekas nav atzīmēts kā
izdevies; 3 = atteikts, jo pēdējā kopija ir jaunāka par 7 dienām (`--force`
ierobežojumu apiet). Rutīnas statusā (`print_routine`) rinda «Ārējā DB kopija»
brīdina, ja kopijas nav vai tā ir vecāka par 8 dienām.

**Ko skripts dara katrā skrējienā.**

1. Momentuzņēmums ar SQLite tiešsaistes kopēšanas API (dzīvo failu nekopē)
   pagaidu mapē `.scratch/backup_tmp/` E: diskā.
2. Saspiež ar `zstd`, šifrē ar `gpg` (AES256, simetriski, frāze no
   `BACKUP_PASSPHRASE_FILE`).
3. **Atjaunošanas pārbaude pirms augšupielādes:** atšifrē, atspiež,
   `PRAGMA integrity_check` jābūt `ok`, un `claims`, `documents`,
   `contradictions`, `context_notes` rindu skaitiem jāsakrīt ar momentuzņēmumu.
   Jebkura neatbilstība — nekas netiek augšupielādēts.
4. Augšupielādē `atmina-YYYY-MM-DD.db.zst.gpg`, `csp-YYYY-MM-DD.db.zst.gpg` un
   `atmina-YYYY-MM-DD.sha256`, pārbauda sha256 galamērķī.
5. Patur jaunākos `BACKUP_KEEP` datumus (noklusējums 4); dzēš tikai failus ar
   šo nosaukuma paraugu.
6. Ieraksta `logs.action='db_backup'` (izmēri, skaiti, sha256, galamērķa veids —
   bez ceļa vai frāzes). Pagaidu faili tiek dzēsti vienmēr.

**Paroles frāze.** Fails `BACKUP_PASSPHRASE_FILE` atrodas ārpus repo. Frāzi
**obligāti glabā arī paroļu pārvaldniekā** — ja tā ir tikai šajā datorā, kopija
pēc datora zuduma nav atšifrējama un tātad nederīga.

**Atjaunošana** (Git Bash; `<frāzes fails>` — fails ar frāzi, piem. no paroļu
pārvaldnieka):

```bash
cd D:/atmina-backups
sha256sum -c atmina-YYYY-MM-DD.sha256
gpg --batch --pinentry-mode loopback --no-symkey-cache \
    --passphrase-file "<frāzes fails>" --decrypt atmina-YYYY-MM-DD.db.zst.gpg \
  | zstd -d -o atmina-atjaunota.db
E:/atmina/.venv/Scripts/python.exe -c "import sqlite3; print(sqlite3.connect('atmina-atjaunota.db').execute('PRAGMA integrity_check').fetchone()[0])"   # jābūt: ok
```

(Šajā datorā `sqlite3` komandrindas rīka nav, tāpēc pārbaude iet caur Python.)

Tikai pēc `ok` apturi visus procesus, kas raksta DB, pārvieto bojāto
`data/atmina.db` (ar `-wal`/`-shm`) malā un ieliec atjaunoto tās vietā.
`csp.db` atjauno tāpat.
