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
   un GB; izpildīto dzēšanu pieraksta CHANGELOG (faili ir untracked, tāpēc
   commit diff to neparādīs — CHANGELOG ieraksts ir vienīgā pēda).
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
