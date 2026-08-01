# VAD Phase 1.5 — Resume handoff (mid-execution)

**Use:** Iekopē šo failu pilnu kā prompt jaunā Claude Code sesijā, lai turpinātu Phase 1.5 darbu pēc cooldown perioda vai sesijas pārtraukšanas.

---

Strādāju projektā atmina (Latvijas politiskās caurspīdības platforma). 2026-05-02 vakarā/2026-05-03 naktī palaists Phase 1.5 cleanup darbs uz worktree `.worktrees/vad-phase-1.5` (branch `vad-phase-1.5`). **Daļa darba pabeigta, daļa palika** — VID portāls aktivizējās rate-limit pret mums, vajag cooldown.

## Konteksts

**Plan:** `.worktrees/vad-phase-1.5/docs/superpowers/plans/2026-05-02-vad-phase-1.5.md` (T1-T11, 6 tasks pabeigti).
**Spec:** `docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md` § 15.2 F13/F14/F15.
**Iepriekšējais handoff:** `docs/superpowers/handoff-vad-phase-1.5.md` (sākotnējais).

## Pabeigts (8 commits uz `vad-phase-1.5`)

| Commit | Saturs |
|---|---|
| `1f7d7db` | Plan file |
| `337f793` | T1 — `_NAME_OVERRIDES[161]` Hosams Abu Meri |
| `5387b52` | T2 — test fixture schema (keywords + negative_patterns kolonnas) |
| `f3ceb90` | T3+T4 — A2 disambig filter (`_load_disambig_config` + `_row_passes_disambig` + filter wire-up). 4 jauni testi. |
| `c82636b` | T5 — `VadClient.reset_session()` + orchestrator parse-fail retry (sākotnējā O(n²) versija) |
| `a1f843f` | T6 — `logs/` mkdir |
| `a4c965a` | T7 — `seed_vad_disambig.py` + `cleanup_contaminated_vad.py` |
| `8baf4a6` | **HOT-FIX** retry uz O(n) — retry-map cache + 3-strikes abandon threshold |

26/26 VAD testi PASS. ruff clean. 1031/1034 kopējie pytest testi PASS (3 fail = pre-existing `test_render_chars` baseline drift uz master, NAV regresija).

## DB stāvoklis (production `data/atmina.db`)

Pirms cleanup: 11 pids contaminated, kopā 1221 dekl ar dažādu cilvēku datiem.
Pēc DELETE + partial reingest (ar 2 sweep iterācijām pirms sesijas pārtraukuma):
- pid=146 Andris Bērziņš (ZZS): **31 dekl** ✓ (no 228 contam.; 216 rejected)
- pid=101 Inese Kalniņa (JV): **37 dekl** ✓ (no 205; 171 rejected)
- pid=144 Inga Bērziņa: **2 dekl** ✓ (re-run ar O(n) hot-fix retry; new=2 + present=2 no failed sweep, errs=0, 368 skip_role)
- pid=104 Līga Kļaviņa: **0** — pirmā mēģinājumā ReadTimeout 29 min (re-run nesācies pirms session pause)
- pid=138 Jānis Zariņš: **0** — pirmā ReadTimeout 1 min (re-run nesācies)
- pid=106 Līga Kozlovska: **0** — pirmā stuck retry-loop, killed (re-run nesācies)
- pid=155 Dace Melbārde: **0** — nesākts
- pid=92 Iļja Ivanovs: **0** — nesākts
- pid=25 Viktors Valainis: **0** — nesākts
- pid=132 Jānis Skrastiņš: **0** — nesākts
- pid=107 Linda Liepiņa: **0** — nesākts

Re-run progress (2026-05-03 ~01:21): 1/9 pids pabeigti (144 Inga). Sesija pārtraukta lietotāja izvēles dēļ ("turpināšu rīt"). Background script `bp5u242k4` un monitor `b57ycwpob` killed clean — ne mid-pid.

`tracked_politicians.keywords` JSON visiem 11 pidiem ielādēts ar `vad_disambig` substring whitelist (sk. `scripts/seed_vad_disambig.py`).

Total VAD declarations DB tagad: 2225 (pirms cleanup bija 3376; 1221 dzēsti, 70 jaunas pievienotas).

## Atlikušais darbs

### A. Re-run 8 atlikušos failed pids (galvenā prioritāte)

Pid 144 jau pabeigts re-run iterācijā. Atlikušie: **104, 138, 106, 155, 92, 25, 132, 107** (8 pids).

Cooldown VID anti-scrape mehanismam ja sesija pārtraukta tagadējā vakarā — gaidīt no rīta vai 6+ stundas no 01:25. Pēc tam re-launch background:

```powershell
# Atjauno arī worktree DB no master DB priekš check.sh post-rerun (notikums tagad ne-current)
# Copy-Item "~\atmina\data\atmina.db" "~\atmina\.worktrees\vad-phase-1.5\data\atmina.db" -Force

# Pielāgo $polIds skriptā uz atlikušajiem 8:
# Edit `.worktrees/vad-phase-1.5/scripts/rerun_failed_vad.ps1` rinda 3:
#   $polIds = @(104, 138, 106, 155, 92, 25, 132, 107)

& "~\atmina\.worktrees\vad-phase-1.5\scripts\rerun_failed_vad.ps1" *>&1 | Out-File -Encoding utf8 "~\atmina\logs\vad-phase-1.5-rerun-2.log"
```

NB: `$pid` ir read-only auto-variable PowerShell — skripts JAU izmanto `$polId` (fix in commit pēc 7199eea).

Hot-fix `8baf4a6` ierobežo retry uz max 3 strikes per pid, tāpēc ja VID joprojām limitē — sweep nepiekarsies. Bet ReadTimeout var notikt; tādā gadījumā pid paliek ar 0 dekl.

**Inga Bērziņa case:** ja arī pēc re-run dabū 0 — pieņemt. Viņas hints ir korekti, bet legitimate VAD records nav reachable bez safety-bound paaugstināšanas (Phase 2 backlog). Atstāt 0; rendering parādīs "nav VAD datu" placeholder.

### B. Verify counts post-rerun

```powershell
Set-Location "~\atmina"
$env:PYTHONIOENCODING='utf-8'
& '~\atmina\.venv\Scripts\python.exe' -c "
import sqlite3
con = sqlite3.connect('data/atmina.db')
con.row_factory = sqlite3.Row
print('=== Final post-cleanup counts ===')
for r in con.execute('SELECT tp.id, tp.name, COUNT(vd.id) AS n FROM tracked_politicians tp LEFT JOIN vad_declarations vd ON vd.opponent_id = tp.id WHERE tp.id IN (146,101,144,104,138,106,155,92,25,132,107) GROUP BY tp.id ORDER BY tp.id'):
    print(f'  pid={r[0]:>3}  {r[1]:<28}  n={r[2]}')
print(); print('Total VAD:', con.execute('SELECT COUNT(*) FROM vad_declarations').fetchone()[0])
"
```

### C. T10 — Re-render + check.sh + dry-run deploy

```powershell
Set-Location "~\atmina"
& '~\atmina\.venv\Scripts\python.exe' -c "from src.render import generate_public_site; generate_public_site()"

Set-Location "~\atmina\.worktrees\vad-phase-1.5"
& "C:\Program Files\Git\bin\bash.exe" scripts/check.sh

Set-Location "~\atmina\.worktrees\vad-phase-1.5"
& "C:\Program Files\Git\bin\bash.exe" scripts/deploy.sh --dry-run
```

NB: 3 baseline fail tests `test_render_chars` IR pre-existing drift, NEKAS NAV jāfiksē šo PR ietvaros. Skat. plan T8 piezīmi.

### D. T11 — User approval → real deploy + merge

Pēc dry-run preview parādīšanas lietotājam:
1. Gaidīt apstiprinājumu Telegrammā (chat_id 619646282)
2. `bash scripts/deploy.sh` (real)
3. Merge: `git checkout master; git merge --no-ff vad-phase-1.5; git push origin master`
4. Update `wiki/CHANGELOG.md` (template draft jau iebūvēts worktree commit pending — viduslaikā lietoju **TODO** placeholder reingest skaitlim, jāaizpilda finālajā commit)
5. Update `wiki/index.md` VAD status uz "DEPLOYED 2026-05-03"
6. Memory: rename `memory/project_vad_phase_0_1_done.md` → `project_vad_done.md`
7. Worktree cleanup: `git worktree remove .worktrees\vad-phase-1.5; git branch -d vad-phase-1.5`

## Praktiskie ceļaragi

- **Worktree paterns Windows:** `Set-Location "~\atmina\.worktrees\vad-phase-1.5"; & "C:\Program Files\Git\bin\bash.exe" <cmd>` (skat. memory `feedback_windows_worktree_powershell.md`).
- **Production DB ops:** Run no master cwd ar absolūto worktree script path: `Set-Location "~\atmina"; & python "C:\...\.worktrees\vad-phase-1.5\scripts\<script>.py"`. Tā skripts izmanto worktree code, bet master DB (relative `data/atmina.db`).
- **Worktree's data/atmina.db** ir 124KB stub no fresh checkout. Production DB iekopēta uz worktree (228MB) lai check.sh strādātu.
- **Ja jāuzņem cooldown:** VID `https://www6.vid.gov.lv/VAD` rate-limits pēc rapid sequential requests. Ja ReadTimeout — gaidīt 30+ min pirms re-try.
- **Tee logging Windows:** PowerShell `Tee-Object` raksta UTF-16 LE ar BOM. Lasīt ar `Get-Content -Encoding Unicode`. Bash `tail -f` neredzēs UTF-16 saturu kā tekstu.

## Pirmais solis jaunajā sesijā

1. Read šo failu pilnu.
2. `cd ~\atmina\.worktrees\vad-phase-1.5; git log --oneline -10` lai redzētu pēdējos commits.
3. `python -c "from src.routine import print_routine; print_routine()"` lai pārbaudītu DB stāvokli.
4. Pārbaudi `tracked_politicians.keywords` 11 pidiem (jābūt ielādētiem hints) — ja ir, vari uzreiz pāriet uz step A.
5. Sāc no atlikušā darba sekcijas A.

## Kritiskās invarianti

- NEDRĪKST atkārtoti palaist `cleanup_contaminated_vad.py` (DELETE) — tas dzēstu jau veiksmīgi reingestētos 146+101 pid'us. Re-run notiek caur `ingest_vad_declarations.py --politician <name>` per pid.
- Idempotence: hot-fix retry-map ir per-pid scope; tas neizglābs starp scripts. Bet natural-key dedup nodrošina, ka esošie 31+37 dekl netiek dublēti.
- VAD code path šobrīd ir worktree only — master nezina par tām izmaiņām. Merge notiek T11 pēc deploy.

**Pēdējais commit:** `8baf4a6` (retry hot-fix). Worktree branch `vad-phase-1.5` ahead of master 8 commits.
