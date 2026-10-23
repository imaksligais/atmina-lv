# Pretrunu soļa pārklājums rutīnā — ieviešanas plāns

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rutīnas 3. solis pārbauda VISUS dienas balsotājus (ne «≤5 aktīvākos»), un `print_routine` rāda «pārbaudīti N no M» no datiem, ne no pašziņota skaitļa.

**Architecture:** Divas jaunas funkcijas `src/routine.py`: `hunt_scope(db, day)` (ko jāpārbauda) un `log_hunt_trace(...)` (vienīgais veids, kā rutīna raksta `contradiction_hunt` rindu: `date` no `current_routine_day()`, obligāti `claim_ids` + `politician_ids`). `_check_contradictions` lasa šīs rindas un salīdzina ar `hunt_scope`; vecās rindas (bez sarakstiem) paliek derīgas ar līdzšinējo uzvedību. Prompti saka, kā dispatchēt ⌈balsotāji/5⌉ hunterus ar skaidriem pid sarakstiem.

**Tech Stack:** Python 3.12, sqlite3, pytest (`tests/test_routine.py`).

**Spec:** `docs/audits/2026-10-15-pretrunu-parklajums/README.md` § «Priekšlikums rutīnai ar izmaksām» (operators «jā» 2026-10-15).

## Global Constraints
- Vienmēr `.venv/Scripts/python.exe`; testi nekad neaiztiek prod DB (`tests/conftest.py` § 4–5).
- `claims`/`logs.timestamp` ir LV laiks; rutīnas diena = `src.briefs.routine_day_window(day)` (robeža 05:00), nekad kalendāra diena.
- Balsotājs = politiķis ar ≥1 `saeima_individual_votes.vote IN ('Par','Pret','Atturas')` (Data Contract 4b: apmeklējums nav balss).
- `rejected_candidates` atslēgas nemaina (`tests/test_dashboard_candidates.py`).
- Ārpus-rutīnas medību `date` = `<darbs>-YYYY-MM-DD` (nekad neiezīmē rutīnas dienu).
- Commit ziņojums caur failu (`git commit -F`), beigās `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Helperiem: AIZLIEGTS `git stash`, `git checkout --`, `git restore`, `git reset`.

## Review Focus
1. Pēcpusnakts rakstīšana (00:30 LV) — `log_hunt_trace` bez `day` jāieraksta VAKARDIENA (#656431 defekts). Tests: Task 1 `test_trace_after_midnight_belongs_to_previous_day`.
2. Rinda ar `claim_ids`, bet bez viena dienas balsotāja → `partial`, ne `done` (pats audita defekts). Tests: Task 2 `test_partial_when_a_voter_is_missing`.
3. Vecā formāta rinda (tikai `claims_checked`) vēl nedrīkst kļūt «missing» — vecās dienas citādi kļūst sarkanas. Tests: esošais `test_done_zero_findings_with_hunt_log` paliek zaļš.
4. Dienas pozīcija, ko neviena rinda nenosauc → `partial` ar skaitu. Tests: Task 2 `test_partial_when_a_claim_is_missing`.
5. Vairākas rindas tai pašai dienai (pēcpusdiena + vakars) — pārklājums ir apvienība. Tests: Task 2 `test_union_of_two_rows_is_done`.

---

### Task 1: `hunt_scope` + `log_hunt_trace`

**Files:**
- Modify: `src/routine.py` (pēc `_hunt_logged_for`, ap :958)
- Test: `tests/test_routine.py` (jauna klase `TestHuntTrace`)

**Interfaces:**
- Produces: `hunt_scope(db, day: str) -> dict` ar atslēgām `claim_ids: list[int]`, `politician_ids: list[int]`, `voter_ids: list[int]` (sakārtoti).
- Produces: `log_hunt_trace(*, claim_ids, politician_ids, found: int, rejected_candidates: list, day: str | None = None, denominators: dict | None = None, db_path: str | None = None, now=None, **extra) -> str` — atgriež ierakstīto `date`.

- [x] **Step 1: Failing tests**

```python
from datetime import datetime
from src.routine import hunt_scope, log_hunt_trace


class TestHuntTrace:
    DAY = "2026-04-07"

    def _seed(self, db):
        db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1,'Balsotājs','A'),(2,'Nebalsotājs','B')")
        for pid, ts in ((1, f"{self.DAY} 15:00:00"), (2, f"{self.DAY} 16:00:00"), (1, "2026-04-08 06:00:00")):
            db.execute("INSERT INTO claims (opponent_id, topic, stance, source_url, claim_type, created_at) "
                       "VALUES (?, 'NATO', 'x', ?, 'position', ?)", (pid, f"https://e.lv/{pid}{ts}", ts))
        db.execute("INSERT INTO saeima_votes (id, vote_date) VALUES (1, '2026-04-01')")
        db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, vote, politician_id) VALUES (1,'B','Par',1)")
        db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, vote, politician_id) VALUES (1,'N','Nebalsoja',2)")
        db.commit()

    def test_scope_is_the_routine_day_and_voters_need_a_cast_ballot(self, empty_routine_db):
        db = get_db(empty_routine_db)
        self._seed(db)
        s = hunt_scope(db, self.DAY)
        db.close()
        assert len(s["claim_ids"]) == 2          # 04-08 06:00 rinda pieder nākamajai dienai
        assert s["politician_ids"] == [1, 2]
        assert s["voter_ids"] == [1]             # 'Nebalsoja' nav balss (4b)

    def test_trace_after_midnight_belongs_to_previous_day(self, empty_routine_db):
        day = log_hunt_trace(claim_ids=[1], politician_ids=[1], found=0, rejected_candidates=[],
                             db_path=empty_routine_db, now=datetime(2026, 4, 8, 0, 30))
        assert day == "2026-04-07"
```

`_seed` kolonnas pārbaudi pret `src/schema.sql` (`saeima_votes` var prasīt vairāk NOT NULL lauku — aizpildi tos, ne mainī shēmu).

- [x] **Step 2: Run — FAIL (ImportError)**

Run: `.venv/Scripts/python.exe -m pytest tests/test_routine.py -k TestHuntTrace -v`

- [x] **Step 3: Implement**

```python
def hunt_scope(db, day: str) -> dict:
    """Ko rutīnas 3. solim jāpārbauda dienā *day* (rutīnas diena, 05:00 robeža).

    claim_ids — visas dienas `position` pozīcijas (embedding pāreja katrai);
    voter_ids — no tām politiķi ar ≥1 nodotu balsi (Par/Pret/Atturas, Data
    Contract 4b) — viņiem obligāta hunter strukturālā pāreja (T9).
    """
    from src.briefs import routine_day_window
    window = routine_day_window(day)
    rows = db.execute(
        "SELECT id, opponent_id FROM claims WHERE claim_type = 'position' "
        "AND created_at >= ? AND created_at < ? ORDER BY id", window,
    ).fetchall()
    pids = sorted({r[1] for r in rows})
    voters = sorted(
        r[0] for r in db.execute(
            "SELECT DISTINCT politician_id FROM saeima_individual_votes "
            "WHERE vote IN ('Par','Pret','Atturas') AND politician_id IN (%s)"
            % ",".join("?" * len(pids)), pids,
        )
    ) if pids else []
    return {"claim_ids": [r[0] for r in rows], "politician_ids": pids, "voter_ids": voters}


def log_hunt_trace(*, claim_ids, politician_ids, found: int, rejected_candidates: list,
                   day: str | None = None, denominators: dict | None = None,
                   db_path: str | None = None, now=None, **extra) -> str:
    """Vienīgais rutīnas ceļš `contradiction_hunt` rindai (audits 2026-10-15).

    `date` pēc noklusējuma = current_routine_day(now): ar roku rakstīts datums
    00:30 naktī iezīmēja nākamo dienu kā izpildītu (#656431). Saraksti ir
    obligāti — `_check_contradictions` no tiem rēķina «pārbaudīti N no M».
    """
    from src.briefs import current_routine_day
    from src.db import log_action
    day = day or current_routine_day(now)
    details = {"date": day, "claim_ids": sorted(set(claim_ids)),
               "politician_ids": sorted(set(politician_ids)), "claims_checked": len(set(claim_ids)),
               "found": found, "rejected_candidates": rejected_candidates, **extra}
    if denominators:
        details["denominators"] = denominators
    log_action("contradiction_hunt", details=details, db_path=db_path)
    return day
```

- [x] **Step 4: Run — PASS** (tā pati komanda)
- [x] **Step 5: Commit** — `src/routine.py tests/test_routine.py`, ziņa «Rutīna: hunt_scope + log_hunt_trace (pretrunu pēda ar sarakstiem)».

### Task 2: `_check_contradictions` rēķina pārklājumu

**Files:**
- Modify: `src/routine.py:931-1013` (`_hunt_logged_for` → `_hunt_rows_for`; `_check_contradictions`)
- Test: `tests/test_routine.py` (klase `TestHuntCoverage`)

**Interfaces:**
- Consumes: `hunt_scope`, `log_hunt_trace` (Task 1).
- Produces: `_hunt_rows_for(db, target_date) -> list[dict]` (parsētas rindas; vecā rinda bez JSON → `{}`); `_hunt_logged_for` = `bool(_hunt_rows_for(...))`. `_check_contradictions` statusi: `done` / `partial` / `missing` / `n/a`.

- [x] **Step 1: Failing tests** (rindas raksta ar `log_hunt_trace` — testi lasa to, ko raksta rakstītājs)

```python
class TestHuntCoverage:
    DAY = TestHuntTrace.DAY

    def _setup(self, path):
        db = get_db(path)
        TestHuntTrace()._seed(db)
        return db, hunt_scope(db, self.DAY)

    def test_done_when_all_claims_and_voters_are_named(self, empty_routine_db):
        db, s = self._setup(empty_routine_db)
        log_hunt_trace(claim_ids=s["claim_ids"], politician_ids=s["voter_ids"], found=0,
                       rejected_candidates=[], day=self.DAY, db_path=empty_routine_db)
        r = _check_contradictions(db, self.DAY)
        db.close()
        assert r["status"] == "done" and "balsotāji 1/1" in r["details"]

    def test_partial_when_a_voter_is_missing(self, empty_routine_db):
        db, s = self._setup(empty_routine_db)
        log_hunt_trace(claim_ids=s["claim_ids"], politician_ids=[], found=0,
                       rejected_candidates=[], day=self.DAY, db_path=empty_routine_db)
        r = _check_contradictions(db, self.DAY)
        db.close()
        assert r["status"] == "partial" and "Balsotājs" in r["details"]

    def test_partial_when_a_claim_is_missing(self, empty_routine_db):
        db, s = self._setup(empty_routine_db)
        log_hunt_trace(claim_ids=s["claim_ids"][:1], politician_ids=s["voter_ids"], found=0,
                       rejected_candidates=[], day=self.DAY, db_path=empty_routine_db)
        r = _check_contradictions(db, self.DAY)
        db.close()
        assert r["status"] == "partial" and "pozīcijas 1/2" in r["details"]

    def test_union_of_two_rows_is_done(self, empty_routine_db):
        db, s = self._setup(empty_routine_db)
        for cids, pids in ((s["claim_ids"][:1], []), (s["claim_ids"][1:], s["voter_ids"])):
            log_hunt_trace(claim_ids=cids, politician_ids=pids, found=0,
                           rejected_candidates=[], day=self.DAY, db_path=empty_routine_db)
        r = _check_contradictions(db, self.DAY)
        db.close()
        assert r["status"] == "done"
```

- [x] **Step 2: Run — FAIL** (`.venv/Scripts/python.exe -m pytest tests/test_routine.py -k "TestHuntCoverage" -v`)

- [x] **Step 3: Implement.** `_hunt_logged_for` ķermeni pārnes uz `_hunt_rows_for`, kas krāj `parsed` dict (vai `{}` vecajām rindām) tur, kur tagad ir `return True`; `_hunt_logged_for` atgriež `bool(_hunt_rows_for(db, target_date))`. `_check_contradictions` — tūlīt pēc `contra_today` aprēķina, PIRMS `if contra_today > 0`:

```python
    rows = _hunt_rows_for(db, target_date)
    traced = [r for r in rows if "claim_ids" in r or "politician_ids" in r]
    if traced:
        scope = hunt_scope(db, target_date)
        named_c = {c for r in traced for c in r.get("claim_ids") or [] if isinstance(c, int)}
        named_p = {p for r in traced for p in r.get("politician_ids") or [] if isinstance(p, int)}
        miss_c = [c for c in scope["claim_ids"] if c not in named_c]
        miss_v = [p for p in scope["voter_ids"] if p not in named_p]
        n_c, n_v = len(scope["claim_ids"]), len(scope["voter_ids"])
        details = (f"pozīcijas {n_c - len(miss_c)}/{n_c}, balsotāji {n_v - len(miss_v)}/{n_v}, "
                   f"{contra_today} pretrunas")
        if not miss_c and not miss_v:
            return {"status": "done", "details": details}
        names = [r[0] for r in db.execute(
            "SELECT name FROM tracked_politicians WHERE id IN (%s) ORDER BY name"
            % ",".join("?" * len(miss_v)), miss_v)] if miss_v else []
        tail = f"; nepārbaudīti balsotāji: {', '.join(names[:5])}" + (" …" if len(names) > 5 else "") if names else ""
        return {"status": "partial", "details": details + tail}
```

`_check_contradictions` docstring/komentārā viena rinda: «jaunā formāta rinda (claim_ids/politician_ids) → pārklājums; vecā → līdzšinējais pierādījums».

- [x] **Step 4: Run** `tests/test_routine.py` pilnībā — PASS (arī vecie `TestCheckContradictions`, after-midnight testi).
- [x] **Step 5: Mutācija** — īslaicīgi izdzēs `or miss_v` nosacījumā (`if not miss_c:`), palaid; `test_partial_when_a_voter_is_missing` jākrīt. Atjauno.
- [x] **Step 6: Commit** — «Rutīna: _check_contradictions rāda pārbaudīti N no M (pozīcijas + balsotāji)».

### Task 3: Prompti — rutīna dispatchē pēc tvēruma

**Files:**
- Modify: `.claude/commands/dienas-rutina.md` 3. solis (ap :51–56)
- Modify: `.claude/agents/contradiction-hunter.md` (:72 circuit breaker, :141 temporālais baseins, Step 5 izvade)

- [x] **Step 1: `dienas-rutina.md` 3. solī** aizstāj `log_action(...)` piemēru ar:

```markdown
   **Tvērums no datiem (kopš 2026-10-15, audits `docs/audits/2026-10-15-pretrunu-parklajums/`).** Pirms medībām:
   ```bash
   .venv/Scripts/python.exe -c "from src.db import get_db; from src.briefs import current_routine_day; from src.routine import hunt_scope; print(hunt_scope(get_db(), current_routine_day()))"
   ```
   `voter_ids` sadali grupās pa ≤5 un dispatchē ⌈balsotāji/5⌉ `@contradiction-hunter` paralēli, katram SKAIDRU pid sarakstu ar viņu dienas claim id — nekad «aktīvākos» (tā 30 d palika nepārbaudīti 13 balsotāji). Cena ≈ 39k Opus tokenu uz politiķi (~600k dienā pie 16 balsotājiem). Pēda — tikai caur:
   ```bash
   .venv/Scripts/python.exe -c "from src.routine import log_hunt_trace; log_hunt_trace(claim_ids=[...], politician_ids=[...], found=<M>, rejected_candidates=[...])"
   ```
   `claim_ids` = pozīcijas, kurām izpildīta embedding pāreja (ekstrakcijas aģenti); `politician_ids` = balsotāji, kuriem hunter izpildīja strukturālo pāreju. `date` NERAKSTI ar roku. `print_routine` rāda «pozīcijas N/M, balsotāji K/L»; `partial` = vēl jāpārbauda nosauktie. Ārpus rutīnas medības: `day='<darbs>-YYYY-MM-DD'`.
```

Saglabā rindkopu par `rejected_candidates` (:56) nemainītu.

- [x] **Step 2: `contradiction-hunter.md`** — pie :72 pievieno: «Ja orķestrators dod skaidru pid sarakstu (rutīnas 3. solis, `/deep-check`), pārbaudi TIEŠI tos; Step 0 «aktīvāko» atlase un ≥5 temporālā baseina slieksnis tad nepiemērojas — mazu vēsturi salīdzini, kāda ir, un denominatoros raksti «zem baseina».» Step 5 izvadē: «`rejected_candidates.claim_new` vienmēr ir `position` id; balsojuma pusi raksti `vote_id` vai `claim_old` (2026-10-15: hunteris samainīja 8 ierakstos).»
- [x] **Step 3:** `bash scripts/check.sh` (`CHECK_PYTEST_WORKERS=3`) — zaļš; citē izvadi.
- [x] **Step 4:** Dzīvais mēģinājums uz prod (tikai lasa): `print_routine()` 2026-10-14 (vecās rindas → `done` kā līdz šim) un `hunt_scope` šodienai — skaitļi saprātīgi.
- [x] **Step 5:** CHANGELOG 2026-10-15 (4) ≤5 rindas; backlog vienums «Pretrunu pārbaudes pārklājums» → IZPILDĪTS ar norādi; commit.
