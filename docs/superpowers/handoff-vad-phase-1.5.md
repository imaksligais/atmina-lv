# VAD Phase 1.5 — Fresh session handoff prompt

**Use:** kopē šo failu pilnu kā prompt jaunā Claude Code sesijā.

---

Strādāju projektā atmina (Latvijas politiskās caurspīdības platforma). Iepriekšējā sesijā 2026-05-02 ielikām produkcijā **VID amatpersonu deklarāciju (VAD) ielādes sistēmu** — Phase 0 (ingest) + Phase 1 (UI tab politiķa profilā ar gads-pa-gadam delta marķieriem). Tagad nepieciešams **Phase 1.5 cleanup** pirms publiska deploy.

## Konteksts

**Spec:** `docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md` — pilns dizains ar § 15.2 audit trail (F11-F15).
**Plāns:** `docs/superpowers/plans/2026-05-02-vad-deklaracijas-plan.md` — 19 task implementācija (visi closed Phase 0+1).
**Runbook:** `wiki/operations/vad-declarations.md`.
**CHANGELOG:** trīs ieraksti zem 2026-05-02.

## Pašreizējais stāvoklis (post-sweep 2026-05-02 19:30)

- 143/152 tracked politiķi (94.1%) ar VAD datiem
- 3376 deklarācijas DB (10797 income, 8543 positions, 7542 family, 6827 NĪ utt.)
- Visi 174 politiķu profili re-renderēti ar Deklarācijas tab
- 54 VAD testi PASS, ruff clean, char fixtures REGEN'd

## Trīs problēmas, kas bloķē deploy

### 1. Homonīmu kontaminācija (PRIORITY — reputational risk)

VID search ar full Vārds+Uzvārds atgriež daudz dažādu personu vairākiem politiķiem ar parastiem vārdiem. Mēs ielādējām visu zem viena `opponent_id` → DB satur sajauktu personu datus.

**Top kontaminētie pids:**
- pid=146 Andris Bērziņš → 228 dekl (mix bijušais prezidents + Saeimas deputāts + citi)
- pid=101 Inese Kalniņa → 205
- pid=? Inga Bērziņa → 184
- pid=104 Līga Kļaviņa → 137
- pid=? Dace Melbārde → 72
- pid=140 Viesturs Zariņš → 91
- pid=138 Jānis Zariņš → 72
- pid=? Iļja Ivanovs → 65
- pid=? Jānis Skrastiņš → 56
- pid=? Viktors Valainis → 56 (sweep arī uzrādīja `errs=171` šim politiķim — high contamination)
- pid=? Līga Kozlovska → 72

**Pārbaudes vaicājums:**
```python
import sqlite3
con = sqlite3.connect("data/atmina.db")
con.row_factory = sqlite3.Row
for r in con.execute("""
    SELECT tp.id, tp.name, COUNT(vd.id) AS n
    FROM tracked_politicians tp
    JOIN vad_declarations vd ON vd.opponent_id = tp.id
    GROUP BY tp.id HAVING n >= 50 ORDER BY n DESC
"""):
    print(f"  pid={r['id']:>3}  {r['name']:<30} {r['n']} dekl")
```

**Vajadzīga risinājuma stratēģija:**
- Variants A: paplašināt `src/vad/declarations.py` ar `_disambiguate_search_rows()` funkciju, kas filtrē VID rindas pa **3rd disambiguator** — institūcija substring no `tracked_politicians.role` vai `keywords` JSON.
- Variants B: `negative_patterns` JSON kolonnā uz `tracked_politicians`, kas satur substringus, kuri **nedrīkst** parādīties VID-row institūcijā/amatā (memory `project_matcher_role_integrity` paterns).
- Variants C: hide kontaminētos politiķus no UI līdz manuāla cleanup (selektīvs `vad_count` overlay).

**Rekomendācija:** sākt ar Variantu A (institūcija filter), pievienojot per-pid `_NAME_OVERRIDES`-stila dictu `_DISAMBIG_HINTS` ar substring catch-list. DELETE + targeted re-ingest.

### 2. Parse-fail UUIDs (1304 cases)

Sweep laikā ~1304 detail fetch atgrieza HTML bez `<table>` (parser raise ValueError "nav header table"). Iespējams VID anti-scrape mechanism — pēc N rapid sequential requests dažas UUID nonces tiek invalidated, detail returnē redirect/error page.

**Vajadzīga risinājuma stratēģija:**
- Pievienot `VadClient.fetch_detail` retry logic — ja parse fails, palaist `_ensure_session()` no jauna (warmup uz `/VAD`), tad re-search un re-fetch jaunā UUID.
- Max 2 attempts; pēc 2nd fail log warn un skip.

### 3. Hosams Abu Meri name override

`Hosams Abu Meri` (pid 161, Veselības ministrs) — naïve split dod `("Hosams Abu", "Meri")` kas nav VID portāla pareizais vārds. Vajag `_NAME_OVERRIDES` entry `src/vad/matcher.py:17`:

```python
_NAME_OVERRIDES: dict[int, tuple[str, str]] = {
    161: ("Hosams", "Abu Meri"),
}
```

## Praktiskie ceļaragi

- **Worktree paterns:** šī sesija strādāja uz master. Phase 1.5 ieteicams atsevišķā worktree (`git worktree add .worktrees/vad-phase-1.5 -b vad-phase-1.5`).
- **DB:** `data/atmina.db` (WAL, foreign_keys ON via `get_db()`).
- **Python:** `& '~\atmina\.venv\Scripts\python.exe'`, `$env:PYTHONIOENCODING='utf-8'`.
- **Commits:** file-based message via `git commit -F .git-commit-msg.tmp` (Latvian/em-dash safe).
- **VID throttle:** 10s search, 3s detail; nevar saīsināt (F12 atklājums).
- **Idempotence:** natural key `(opponent_id, declaration_kind, declaration_year, submitted_at, position_title)` — DELETE + re-ingest drošs.

## Pirmais solis

1. Palaist `print_routine()` lai pārbaudītu DB stāvokli un atgūt kontekstu.
2. Read spec § 15.2 audit trail (F11-F15) un § 9.5 family policy.
3. Iesāc no Variantu A (homonīmu disambiguation) — augstākais reputational risk.

Pēc Phase 1.5 → re-render + check.sh + `bash scripts/deploy.sh --dry-run` → ja ok, lietotāja apstiprinājums → reāls deploy.

**Iepriekšējās sesijas final commit:** `b0718c6` (test(fixtures): REGEN render_baseline_*).
