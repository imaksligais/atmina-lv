# Nedēļas stāsti — ieviešanas plāns

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nedēļas pārskats kļūst par 3–5 stāstiem, ko aģents izvēlas no koda sagatavota kandidātu saraksta; vecā tēmu/bloku forma skeletā pazūd.

**Architecture:** Jauna tīra lasīšanas funkcija `weekly_story_candidates(db, week_start)` (`src/briefs.py`) savāc septiņu veidu signālus; `generate_weekly_brief()` tos ieraksta skeletā kā HTML komentāru un dod jaunās sadaļas. Balsojumu dati iznākti kopīgā palīgfunkcijā, lai kandidāti un `weekly_vote_breakdown()` nekad neatšķirtos. Validators, priekšskats, LV linteris un aģentu prompti pielāgoti jaunajai formai; vecie pārskati paliek derīgi.

**Tech Stack:** Python 3.12, SQLite, pytest, Jinja2 (render), markdown aģentu prompti.

**Spec:** `docs/superpowers/specs/2026-11-01-nedelas-stasti-design.md` (operators apstiprināja 2026-11-01). Izpildītājs lasa abus.

## Global Constraints

- Vienmēr `.venv/Scripts/python.exe`, nekad kails `python`. Testi: `.venv/Scripts/python.exe -m pytest <ceļš> -q`.
- Testi nekad neaiztiek dzīvo DB (`tests/conftest.py` § 4–5); katrs tests veido savu DB `tmp_path`.
- Commit ziņa caur failu: `git commit -F <fails>`; ziņas beigās `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Palīgi nedrīkst palaist `git stash`, `git checkout --`, `git restore`, `git reset`.** Nekomitētie `docs/social/`, `docs/tweet_bank/` faili nav šī darba daļa — neaiztikt, nepievienot.
- «Publicēta pretruna» = `COALESCE(confirmed, 1) = 1 AND withdrawn_at IS NULL` — tas pats filtrs, ko lieto publiskās virsmas un `routine_week_contradiction_count` (NULL = mantota publicēta rinda; spec rakstīja `confirmed=1`).
- NEEDS_REVIEW pozīcijas kandidātos izslēgtas vienmēr: `c.review_status IS NOT 'needs_review'` (`_NOT_NEEDS_REVIEW_SQL`).
- `political_tensions.created_at` ir UTC → salīdzina `datetime(t.created_at, 'localtime')` ar `routine_day_window()` robežām. `contradictions.detected_at`, `claims`, `context_notes` ir LV laiks → bez modifikatora (T17). `tests/test_timestamp_timezone_gate.py` skenē visus string literāļus `src/` — `'localtime'` rakstīt tikai īstā izsaukumā uz īstas kolonnas.
- Koalīcija balsojuma brīdī tikai caur `src.coalition.coalition_periods()` + `coalition_at()`; partiju statusam `get_coalition_map()`. Nekad `relationship_type`.
- Stringiem, ko lasa cilvēks (latviski): gramatika + garumzīmes; bez «brief», bez kalkiem.
- H1 jaunajā formā: `# Nedēļas stāsti — YYYY-MM-DD līdz YYYY-MM-DD` (ISO datumi; `src/render/blog.py:697` ņem kartītes datumu diapazonu no divām ISO datumu virknēm virsrakstā, un `display_title` regex `blog.py:624` nogriež tikai beigu «— datums», ne «līdz datums»). Spec rāda `<sākums> – <beigas>` neformatēti — šis ir tā precizējums.
- `context_notes.topic` paliek `nedēļas analīze START līdz END` (no tā atkarīgs `_previous_forward_look` un slug).
- **Lint 7. likums ir globāls:** `lint_lv_style` nezina pārskata veidu, tāpēc «iezīmē» sāks krist arī dienas pārskatos (mērījums: 17 no 63 dienas pārskatiem kopš 2026-09-01). Tas ir apzināti; operatoram par to pasaka.
- Vecie nedēļas pārskati DB netiek mainīti un joprojām renderējas (vecās formas validācija un priekšskats paliek).

## Review Focus

1. **Nedēļa bez neviena kandidāta** (klusa nedēļa, Saeima nesēž) — skelets joprojām ģenerējas, komentārā `STORY_CANDIDATES (0)`, nekāda kļūda. Tests 4. uzdevumā.
2. **Kandidāta teksts satur `-->`** (politiķa citāts virsrakstā, pagājušās nedēļas punkts) — komentārs nedrīkst aizvērties agri, citādi iekšējais saraksts nonāk publiskajā lapā. Tests 4. uzdevumā.
3. **Aģents aizmirst izdzēst kandidātu komentāru** — `store_context_note` atsaka (validators), nevis klusi glabā. Tests 5. uzdevumā.
4. **Pēc pirmā jaunā pārskata nākamās nedēļas `followup` ir tukšs**, jo jaunajā formā sadaļa saucas `## Ko gaidīt`, ne `## Skats uz priekšu`. Abas jālasa. Tests 1. uzdevumā.
5. **Balsojums ar `⚠ NESAKRĪT`** vai bez `coalition_periods` tabulas (vecs DB) — `vote_split` to izlaiž / nenosauc koalīciju, nevis krīt. Testi 2. uzdevumā.

---

## Failu karte

| Fails | Atbildība | Uzdevums |
|---|---|---|
| `src/briefs.py` | `weekly_story_candidates()` + palīgi; `_week_vote_data()`; `_previous_forward_look()` abi virsraksti; jaunais `generate_weekly_brief()` skelets | 1–4 |
| `src/tools.py` | `_validate_brief_structure` weekly zars: jaunā + vecā forma | 5 |
| `src/render/blog.py` | `_brief_preview` jaunās formas pirmais stāsts | 5 |
| `src/lv_style.py` | 7. likums `analytic-filler-iezime`, `RULES_TOTAL = 7` | 6 |
| `tests/test_weekly_story_candidates.py` (jauns) | kandidātu testi (unit + slieksnis) | 1–3 |
| `tests/test_briefs_weekly.py`, `tests/test_briefs.py` | vecās skeleta formas testu dzēšana/pārrakstīšana | 4 |
| `tests/test_weekly_stories_e2e.py` (jauns) | viens E2E: skelets → glabāšana → renderēšana | 5 |
| `tests/test_tools.py`, `tests/test_landing_preview_and_active.py`, `tests/test_lv_style.py` | jaunās formas gadījumi blakus vecajiem | 5–6 |
| `.claude/agents/weekly-brief-writer.md`, `.claude/agents/quality-reviewer.md`, `wiki/operations/weekly-routine.md`, `wiki/CHANGELOG.md` | prompti, runbooks, lēmuma ieraksts | 7 |

Kandidāta forma (visiem veidiem vienāda, lai skelets un aģents lasa vienu struktūru):

```python
{
    "kind": str,              # contradiction | vote_split | daily_lead | topic_surge | tension_pair | followup | new_voice
    "fact": str,              # viena rinda, latviski, bez jaunrindām
    "topic": str | None,
    "days": list[str],        # ISO datumi, sakārtoti
    "claim_ids": list[int],
    "vote_ids": list[int],
    "contradiction_ids": list[int],
    "repeated": bool,         # tikai daily_lead: tā pati tēma vadīja ≥2 dienas; citiem False
}
```

---

### Task 1: `weekly_story_candidates()` — pretrunas, tēmu lēcieni, spriedzes, jaunas balsis, followup

**Files:**
- Modify: `src/briefs.py` (`_previous_forward_look` ~1059–1096; jaunas funkcijas tieši pēc tās)
- Create: `tests/test_weekly_story_candidates.py`

**Interfaces:**
- Produces: `weekly_story_candidates(db, week_start: str) -> list[dict]` (db = atvērts `sqlite3.Connection` ar `row_factory=Row`, kā `get_db()` dod; funkcija to NEaizver). Konstantes `SURGE_MIN_POSITIONS = 8`, `SURGE_MIN_RATIO = 2.0`, `NEW_VOICE_LOOKBACK_DAYS = 30`, `_STORY_KIND_ORDER`. Palīgs `_cand(kind, fact, **kw) -> dict`.
- `_previous_forward_look(db, week_start)` tagad lasa gan `## Skats uz priekšu`, gan `## Ko gaidīt`.

- [ ] **Step 1: Uzraksti krītošos testus**

```python
# tests/test_weekly_story_candidates.py
"""Nedēļas stāstu kandidāti (spec 2026-11-01 § 2)."""
from src.db import init_db, get_db

WEEK = "2026-05-25"  # pirmdiena; nedēļa 05-25..05-31


def _db(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)  # testi padod tmp_path / "a"
    path = str(tmp_path / "t.db")
    init_db(path)
    db = get_db(path)
    db.execute("INSERT INTO parties (name, short_name, coalition_status) VALUES ('Jaunā Vienotība','JV','coalition')")
    for pid, name, rel in ((1, "Aļģis Bērziņš", "tracked"), (2, "Cits Kalniņš", "tracked"),
                           (3, "Žurnālists Ozols", "journalist"), (4, "Vecais Liepa", "inactive")):
        db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) "
                   "VALUES (?,?,'Jaunā Vienotība',?)", (pid, name, rel))
    db.commit()
    return db


_DID = [1000]


def _claim(db, pid, topic, day, reasoning=None):
    _DID[0] += 1
    did = _DID[0]
    db.execute("INSERT INTO documents (id, platform, source_url, content, content_hash, scraped_at) "
               "VALUES (?, 'web', ?, 'x', ?, ?)", (did, f"https://e.lv/{did}", f"h{did}", day))
    cur = db.execute(
        "INSERT INTO claims (opponent_id, document_id, topic, stance, source_url, stated_at, "
        "claim_type, reasoning) VALUES (?,?,?,'s',?,?,'position',?)",
        (pid, did, topic, f"https://e.lv/{did}", day, reasoning))
    return cur.lastrowid


def _kinds(cands, kind):
    return [c for c in cands if c["kind"] == kind]


def _surge_db(tmp_path, week_n, prior_n):
    db = _db(tmp_path)
    for i in range(week_n):
        _claim(db, 1, "Korupcija un KNAB", "2026-05-27")
    for i in range(prior_n):  # iepriekšējās 4 nedēļas: 04-27..05-24
        _claim(db, 1, "Korupcija un KNAB", "2026-05-10")
    db.commit()
    return db


def test_topic_surge_needs_eight_positions(tmp_path):
    from src.briefs import weekly_story_candidates
    assert not _kinds(weekly_story_candidates(_surge_db(tmp_path / "a", 7, 0), WEEK), "topic_surge")
    assert _kinds(weekly_story_candidates(_surge_db(tmp_path / "b", 8, 0), WEEK), "topic_surge")


def test_topic_surge_needs_double_the_four_week_average(tmp_path):
    from src.briefs import weekly_story_candidates
    # 19 pret vidēji 10 (40/4) = ×1,9 → nav; 20 pret 10 = ×2,0 → ir
    assert not _kinds(weekly_story_candidates(_surge_db(tmp_path / "a", 19, 40), WEEK), "topic_surge")
    surge = _kinds(weekly_story_candidates(_surge_db(tmp_path / "b", 20, 40), WEEK), "topic_surge")
    assert surge and surge[0]["topic"] == "Korupcija un KNAB"


def test_topic_surge_without_history_counts_at_eight(tmp_path):
    from src.briefs import weekly_story_candidates
    (c,) = _kinds(weekly_story_candidates(_surge_db(tmp_path, 8, 0), WEEK), "topic_surge")
    assert "8" in c["fact"] and len(c["claim_ids"]) == 8


def test_needs_review_never_counts(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _db(tmp_path)
    for _ in range(7):
        _claim(db, 1, "Korupcija un KNAB", "2026-05-27")
    nr = _claim(db, 1, "Korupcija un KNAB", "2026-05-27", reasoning="NEEDS_REVIEW: x")
    db.commit()
    cands = weekly_story_candidates(db, WEEK)
    assert not _kinds(cands, "topic_surge")
    assert all(nr not in c["claim_ids"] for c in cands)


def test_published_contradiction_in_routine_window(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _db(tmp_path)
    old = _claim(db, 1, "Budžets", "2026-03-01")
    new = _claim(db, 1, "Budžets", "2026-05-27")
    rows = [  # (confirmed, detected_at, withdrawn_at)
        (1, "2026-05-27 18:00:00", None),       # ir
        (None, "2026-06-01 02:00:00", None),    # mantota publicēta, svētdienas rutīna pēc pusnakts → ir
        (0, "2026-05-27 18:00:00", None),       # kandidāts → nav
        (-1, "2026-05-27 18:00:00", "2026-05-28"),  # atsaukta → nav
        (1, "2026-05-25 04:00:00", None),       # iepriekšējās nedēļas rutīnas diena → nav
    ]
    for conf, det, wd in rows:
        db.execute("INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id, topic, "
                   "summary, severity, confirmed, detected_at, withdrawn_at) "
                   "VALUES (1,?,?,'Budžets','Kopsavilkums --> x','reversal',?,?,?)",
                   (old, new, conf, det, wd))
    db.commit()
    got = _kinds(weekly_story_candidates(db, WEEK), "contradiction")
    assert len(got) == 2
    assert got[0]["claim_ids"] == [old, new]
    assert "Aļģis Bērziņš" in got[0]["fact"]


def test_tension_pair_needs_two_in_routine_week(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _db(tmp_path)
    # UTC laiks: 2026-05-31 22:30 UTC = 06-01 01:30 LV → vēl svētdienas rutīnas diena
    for ts in ("2026-05-26 10:00:00", "2026-05-31 22:30:00"):
        db.execute("INSERT INTO political_tensions (source_pid, target_pid, topic, description, created_at) "
                   "VALUES (1, 2, 'Budžets', 'd', ?)", (ts,))
    db.execute("INSERT INTO political_tensions (source_pid, target_pid, topic, description, created_at) "
               "VALUES (2, 1, 'Budžets', 'd', '2026-05-26 10:00:00')")  # pretējā virzienā — viena
    db.commit()
    (c,) = _kinds(weekly_story_candidates(db, WEEK), "tension_pair")
    assert c["fact"].startswith("Aļģis Bērziņš → Cits Kalniņš")
    assert "2" in c["fact"]


def test_new_voice_excludes_inactive_and_audience(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _db(tmp_path)
    _claim(db, 1, "A", "2026-05-27")           # 1: jauns
    _claim(db, 2, "A", "2026-05-27")
    _claim(db, 2, "A", "2026-05-10")           # 2: runāja 30 dienās → nav jauns
    _claim(db, 3, "A", "2026-05-27")           # žurnālists → nav
    _claim(db, 4, "A", "2026-05-27")           # inactive → nav
    db.commit()
    got = _kinds(weekly_story_candidates(db, WEEK), "new_voice")
    assert [c["fact"].split(" (")[0] for c in got] == ["Aļģis Bērziņš"]


def test_followup_reads_both_forward_look_headings(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _db(tmp_path)
    prev = ("# Nedēļas stāsti — 2026-05-18 līdz 2026-05-24\n\n## Stāsts\n\nx\n\n"
            "## Ko gaidīt\n\n- Otrdien, 26. maijā, Saeimas sēde.\n\n"
            "## Nedēļa skaitļos\n\n")
    db.execute("INSERT INTO context_notes (opponent_id, note_type, topic, content, created_at) "
               "VALUES (NULL, 'weekly_brief', 'nedēļas analīze 2026-05-18 līdz 2026-05-24', ?, "
               "'2026-05-25 09:00:00')", (prev,))
    db.commit()
    (c,) = _kinds(weekly_story_candidates(db, WEEK), "followup")
    assert c["fact"] == "- Otrdien, 26. maijā, Saeimas sēde."
```

- [ ] **Step 2: Palaid un pārliecinies, ka krīt**

Run: `.venv/Scripts/python.exe -m pytest tests/test_weekly_story_candidates.py -q`
Expected: FAIL — `ImportError: cannot import name 'weekly_story_candidates'`.

- [ ] **Step 3: Implementē**

`_previous_forward_look`: aizvieto `if line.strip() == _FORWARD_LOOK_HEADING:` ar `if line.strip() in _FORWARD_LOOK_HEADINGS:` un definē:

```python
_FORWARD_LOOK_HEADING = "## Skats uz priekšu"
# Jaunā forma (2026-11-01) sauc to pašu sadaļu «Ko gaidīt»; abas jālasa, citādi
# nedēļa pēc pirmā jaunā pārskata paliek bez followup kandidātiem.
_FORWARD_LOOK_HEADINGS = (_FORWARD_LOOK_HEADING, "## Ko gaidīt")
```

Pēc `_previous_forward_look` pievieno:

```python
SURGE_MIN_POSITIONS = 8
SURGE_MIN_RATIO = 2.0
NEW_VOICE_LOOKBACK_DAYS = 30
_STORY_KIND_ORDER = ("contradiction", "vote_split", "daily_lead", "topic_surge",
                     "tension_pair", "followup", "new_voice")
_AUDIENCE_REL_TYPES = ("journalist", "influencer", "neutral", "inactive", "organization")


def _cand(kind: str, fact: str, *, topic=None, days=(), claim_ids=(), vote_ids=(),
          contradiction_ids=(), repeated=False) -> dict:
    return {
        "kind": kind,
        "fact": " ".join(str(fact).split()),
        "topic": topic,
        "days": sorted(set(days)),
        "claim_ids": list(claim_ids),
        "vote_ids": list(vote_ids),
        "contradiction_ids": list(contradiction_ids),
        "repeated": repeated,
    }


def _ids(csv: str | None) -> list[int]:
    return [int(x) for x in (csv or "").split(",") if x]


def _cands_contradiction(db, week_start, week_end):
    lo, hi = routine_day_window(week_start)[0], routine_day_window(week_end)[1]
    out = []
    for r in db.execute(
        "SELECT c.id, c.topic, c.severity, c.headline, c.summary, c.claim_old_id, "
        "c.claim_new_id, c.detected_at, p.name, p.party FROM contradictions c "
        "JOIN tracked_politicians p ON p.id = c.opponent_id "
        "WHERE c.detected_at >= ? AND c.detected_at < ? "
        "AND COALESCE(c.confirmed, 1) = 1 AND c.withdrawn_at IS NULL ORDER BY c.id",
        (lo, hi),
    ):
        label = _SEVERITY_LV.get(r["severity"] or "", "pretruna")
        what = r["headline"] or contradiction_excerpt_text(r["summary"], 25)
        out.append(_cand(
            "contradiction",
            f"{r['name']} ({r['party'] or '—'}), {r['topic']}: {label} — {what}",
            topic=r["topic"], days=[str(r["detected_at"])[:10]],
            claim_ids=[i for i in (r["claim_old_id"], r["claim_new_id"]) if i],
            contradiction_ids=[r["id"]]))
    return out


def _cands_topic_surge(db, week_start, week_end):
    prior_start = (datetime.strptime(week_start, "%Y-%m-%d") - timedelta(days=28)).strftime("%Y-%m-%d")
    prior_end = (datetime.strptime(week_start, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    prior = {r["topic"]: r["n"] for r in db.execute(
        "SELECT c.topic, COUNT(*) AS n FROM claims c WHERE date(c.stated_at) BETWEEN ? AND ? "
        f"AND c.claim_type = 'position' AND {_NOT_NEEDS_REVIEW_SQL} GROUP BY c.topic",
        (prior_start, prior_end))}
    out = []
    for r in db.execute(
        "SELECT c.topic, COUNT(*) AS n, GROUP_CONCAT(c.id) AS ids, "
        "GROUP_CONCAT(DISTINCT date(c.stated_at)) AS days FROM claims c "
        "WHERE date(c.stated_at) BETWEEN ? AND ? "
        f"AND c.claim_type = 'position' AND {_NOT_NEEDS_REVIEW_SQL} "
        "GROUP BY c.topic ORDER BY n DESC, c.topic", (week_start, week_end)):
        avg = prior.get(r["topic"], 0) / 4
        if r["n"] < SURGE_MIN_POSITIONS or (avg and r["n"] < SURGE_MIN_RATIO * avg):
            continue
        base = (f"4 iepriekšējās nedēļās vidēji {avg:.1f}".replace(".", ",") if avg
                else "4 iepriekšējās nedēļās nebija")
        out.append(_cand("topic_surge", f"{r['topic']}: {r['n']} pozīcijas; {base}",
                         topic=r["topic"], days=(r["days"] or "").split(","),
                         claim_ids=sorted(_ids(r["ids"]))))
    return out


def _cands_tension_pair(db, week_start, week_end):
    lo, hi = routine_day_window(week_start)[0], routine_day_window(week_end)[1]
    out = []
    for r in db.execute(
        "SELECT t.source_pid, t.target_pid, s.name AS src, g.name AS tgt, COUNT(*) AS n, "
        "GROUP_CONCAT(DISTINCT t.topic) AS topics, "
        "GROUP_CONCAT(DISTINCT date(datetime(t.created_at, 'localtime'))) AS days "
        "FROM political_tensions t "
        "JOIN tracked_politicians s ON s.id = t.source_pid "
        "JOIN tracked_politicians g ON g.id = t.target_pid "
        "WHERE datetime(t.created_at, 'localtime') >= ? AND datetime(t.created_at, 'localtime') < ? "
        "GROUP BY t.source_pid, t.target_pid HAVING COUNT(*) >= 2 ORDER BY n DESC", (lo, hi)):
        topics = (r["topics"] or "").split(",")
        out.append(_cand("tension_pair", f"{r['src']} → {r['tgt']}: {r['n']} spriedzes ({', '.join(topics)})",
                         topic=topics[0] if len(topics) == 1 else None,
                         days=(r["days"] or "").split(",")))
    return out


def _cands_new_voice(db, week_start, week_end):
    lookback = (datetime.strptime(week_start, "%Y-%m-%d")
                - timedelta(days=NEW_VOICE_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    marks = ",".join("?" * len(_AUDIENCE_REL_TYPES))
    out = []
    for r in db.execute(
        f"""SELECT p.id, p.name, p.party, COUNT(*) AS n, GROUP_CONCAT(c.id) AS ids,
                   GROUP_CONCAT(DISTINCT date(c.stated_at)) AS days
            FROM claims c JOIN tracked_politicians p ON p.id = c.opponent_id
            WHERE date(c.stated_at) BETWEEN ? AND ? AND c.claim_type = 'position'
              AND {_NOT_NEEDS_REVIEW_SQL}
              AND COALESCE(p.relationship_type, '') NOT IN ({marks})
              AND NOT EXISTS (SELECT 1 FROM claims c2 WHERE c2.opponent_id = p.id
                    AND c2.claim_type = 'position' AND date(c2.stated_at) >= ?
                    AND date(c2.stated_at) < ?)
            GROUP BY p.id ORDER BY n DESC, p.name""",
        (week_start, week_end, *_AUDIENCE_REL_TYPES, lookback, week_start)):
        out.append(_cand("new_voice",
                         f"{r['name']} ({r['party'] or '—'}): {r['n']} pozīcijas; iepriekšējās "
                         f"{NEW_VOICE_LOOKBACK_DAYS} dienās 0",
                         days=(r["days"] or "").split(","), claim_ids=sorted(_ids(r["ids"]))))
    return out


def weekly_story_candidates(db, week_start: str) -> list[dict]:
    """Nedēļas stāstu kandidāti aģentam (spec 2026-11-01 § 2). Tīra lasīšana;
    savienojumu neaizver. NEEDS_REVIEW pozīcijas izslēgtas visos veidos.
    Secība: `_STORY_KIND_ORDER`, veida iekšienē — kā katrs palīgs sakārtoja."""
    week_end = (datetime.strptime(week_start, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
    cands: list[dict] = []
    cands += _cands_contradiction(db, week_start, week_end)
    cands += _cands_topic_surge(db, week_start, week_end)
    cands += _cands_tension_pair(db, week_start, week_end)
    cands += [_cand("followup", b) for b in _previous_forward_look(db, week_start)]
    cands += _cands_new_voice(db, week_start, week_end)
    order = {k: i for i, k in enumerate(_STORY_KIND_ORDER)}
    return sorted(cands, key=lambda c: order[c["kind"]])  # sorted() ir stabils
```

Pārbaudi, ka `contradiction_excerpt_text` un `_SEVERITY_LV` jau ir definēti `src/briefs.py` pirms šīs vietas (grep); ja `contradiction_excerpt_text` paraksts atšķiras, pielāgo izsaukumu, ne funkciju.

- [ ] **Step 4: Palaid testus**

Run: `.venv/Scripts/python.exe -m pytest tests/test_weekly_story_candidates.py tests/test_briefs_weekly.py tests/test_timestamp_timezone_gate.py -q`
Expected: PASS (arī esošais `test_weekly_skeleton_carries_previous_forward_look`).

- [ ] **Step 5: Mutācijas pārbaude** — īslaicīgi nomaini `SURGE_MIN_POSITIONS = 7` → `test_topic_surge_needs_eight_positions` krīt; atjauno. Nomaini `'localtime'` izsaukumu uz kailu `t.created_at` → tension tests krīt; atjauno.

- [ ] **Step 6: Commit** — `git add src/briefs.py tests/test_weekly_story_candidates.py`; ziņa «Nedēļas stāsti: kandidātu funkcija (pretrunas, tēmu lēcieni, spriedzes, jaunas balsis, followup)».

---

### Task 2: `vote_split` kandidāti un kopīgie balsojumu dati

**Files:**
- Modify: `src/briefs.py` (`weekly_vote_breakdown` ~1099–1215; `weekly_story_candidates`)
- Modify: `tests/test_weekly_story_candidates.py`

**Interfaces:**
- Consumes: `_cand()`, `weekly_story_candidates()` (Task 1); `src.coalition.coalition_periods(db)`, `coalition_at(periods, vote_date, vote_time) -> frozenset | None`.
- Produces: `_week_vote_data(db, week_start, week_end) -> tuple[list[Row], dict[int, dict[str, dict[str, int]]]]` — balsojumi (bez reģistrācijām, sakārtoti pēc datuma/laika/id) un `{vote_id: {frakcija: {"Par","Pret","Atturas","Nebalsoja","cits": int}}}`; tukša frakcija → `_NO_FACTION_LABEL`. `_vote_mismatch(v, facs) -> list[str]` (tukšs = sakrīt). `SPLIT_MIN_MINORITY = 2`.

- [ ] **Step 1: Krītošie testi** (pievieno failam)

```python
def _vote_db(tmp_path, ballots, periods=True, totals=None):
    """Viens balsojums #1 (2026-05-27 10:00, dok. 123/Lp14) + ķēdes balsojums #2 bez šķelšanās."""
    from src.saeima.schema import init_saeima_tables
    path = str(tmp_path / "v.db")
    init_db(path)
    init_saeima_tables(path)
    db = get_db(path)
    par = sum(n for f, v, n in ballots if v == "Par")
    pret = sum(n for f, v, n in ballots if v == "Pret")
    att = sum(n for f, v, n in ballots if v == "Atturas")
    if totals:
        par, pret, att = totals
    for vid, t, p, pr, a in ((1, "10:00", par, pret, att), (2, "11:00", 2, 0, 0)):
        db.execute("INSERT INTO saeima_votes (id, motif, vote_date, vote_time, total_par, total_pret, "
                   "total_atturas, total_nebalso, result, url, document_nr) "
                   "VALUES (?, 'Grozījumi likumā', '2026-05-27', ?, ?, ?, ?, 0, 'Pieņemts', 'u', '123/Lp14')",
                   (vid, t, p, pr, a))
    n = 0
    for faction, vote, count in ballots:
        for _ in range(count):
            n += 1
            db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, faction, vote) "
                       "VALUES (1, ?, ?, ?)", (f"D{n}", faction, vote))
    for k in range(2):
        db.execute("INSERT INTO saeima_individual_votes (vote_id, deputy_name, faction, vote) "
                   "VALUES (2, ?, 'JV', 'Par')", (f"E{k}",))
    if periods:
        db.execute("INSERT INTO coalition_periods (valid_from_date, valid_from_time, factions) "
                   "VALUES ('2026-01-01', '00:00', 'JV,ZZS')")
    db.commit()
    return db


def test_vote_split_inside_faction(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _vote_db(tmp_path, [("JV", "Par", 10), ("JV", "Pret", 2), ("ZZS", "Par", 8)])
    (c,) = _kinds(weekly_story_candidates(db, WEEK), "vote_split")
    assert c["vote_ids"] == [1, 2]          # visa document_nr ķēde (T14)
    assert "JV" in c["fact"] and "123/Lp14" in c["fact"]


def test_one_dissenter_is_not_a_split(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _vote_db(tmp_path, [("JV", "Par", 10), ("JV", "Pret", 1), ("ZZS", "Par", 8)])
    assert not _kinds(weekly_story_candidates(db, WEEK), "vote_split")


def test_coalition_faction_against_its_bloc(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _vote_db(tmp_path, [("JV", "Par", 20), ("ZZS", "Atturas", 8)])
    (c,) = _kinds(weekly_story_candidates(db, WEEK), "vote_split")
    assert "ZZS" in c["fact"] and "Atturas" in c["fact"]


def test_no_coalition_periods_names_no_bloc(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _vote_db(tmp_path, [("JV", "Par", 20), ("ZZS", "Atturas", 8)], periods=False)
    assert not _kinds(weekly_story_candidates(db, WEEK), "vote_split")


def test_mismatched_vote_is_skipped(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _vote_db(tmp_path, [("JV", "Par", 10), ("JV", "Pret", 3)], totals=(10, 4, 0))
    assert not _kinds(weekly_story_candidates(db, WEEK), "vote_split")
```

Ja `coalition_periods` tabulu `init_db` neizveido, pārbaudi `src/db_migrations.py::_apply_coalition_periods` un izsauc to testa palīgā tāpat kā citi testi (grep `coalition_periods` `tests/`).

- [ ] **Step 2: Palaid** — `.venv/Scripts/python.exe -m pytest tests/test_weekly_story_candidates.py -q -k vote` → FAIL (nav `vote_split`).

- [ ] **Step 3: Implementē**

1. Iznes no `weekly_vote_breakdown` bloku no `tables = {...}` līdz `indiv[...]` aizpildīšanai uz `_week_vote_data(db, week_start, week_end)`, kas atgriež `(votes, indiv)` (bez saeima tabulām → `([], {})`). `weekly_vote_breakdown` to izsauc; tā izvade nemainās ne par rakstzīmi.
2. Iznes nesakritības pārbaudi uz:

```python
def _vote_mismatch(v, facs: dict) -> list[str]:
    diffs = []
    for field, total_col in (("Par", "total_par"), ("Pret", "total_pret"), ("Atturas", "total_atturas")):
        got = sum(c[field] for c in facs.values())
        want = v[total_col] or 0
        if got != want:
            diffs.append(f"individuālie {field} {got} ≠ kopā {want}")
    return diffs
```

un lieto to `weekly_vote_breakdown` iekšā.
3. Pievieno:

```python
SPLIT_MIN_MINORITY = 2
_SPLIT_BALLOTS = ("Par", "Pret", "Atturas")


def _majority(c: dict) -> tuple[str, int, int]:
    """(vairākuma balsojums, tā skaits, otrā lielākā skaits) starp Par/Pret/Atturas."""
    ranked = sorted(((c[b], b) for b in _SPLIT_BALLOTS), reverse=True)
    return ranked[0][1], ranked[0][0], ranked[1][0]


def _cands_vote_split(db, week_start, week_end):
    from src.coalition import coalition_at, coalition_periods
    votes, indiv = _week_vote_data(db, week_start, week_end)
    periods = coalition_periods(db)
    chains: dict[str, list] = {}
    for v in votes:
        key = (v["document_nr"] or "").strip() or f"motif:{v['motif'] or ''}"
        chains.setdefault(key, []).append(v)
    out = []
    for key, chain in chains.items():
        notes, days = [], set()
        for v in chain:
            facs = {f: c for f, c in indiv.get(v["id"], {}).items() if f != _NO_FACTION_LABEL}
            if _vote_mismatch(v, indiv.get(v["id"], {})):
                continue
            for f, c in sorted(facs.items()):
                maj, n_maj, n_second = _majority(c)
                if n_second >= SPLIT_MIN_MINORITY:
                    notes.append(f"{v['vote_date']} {v['vote_time'] or ''}: {f} šķēlās "
                                 f"{c['Par']}/{c['Pret']}/{c['Atturas']}")
                    days.add(str(v["vote_date"])[:10])
            coal = coalition_at(periods, v["vote_date"], v["vote_time"] or "") if periods else None
            if coal:
                bloc = {b: sum(facs[f][b] for f in facs if f in coal) for b in _SPLIT_BALLOTS}
                bloc_maj = _majority(bloc)[0]
                for f in sorted(facs):
                    if f not in coal:
                        continue
                    maj, n_maj, _ = _majority(facs[f])
                    if maj != bloc_maj and n_maj >= SPLIT_MIN_MINORITY:
                        notes.append(f"{v['vote_date']} {v['vote_time'] or ''}: koalīcijas {f} "
                                     f"{maj} ({n_maj}), bloks {bloc_maj}")
                        days.add(str(v["vote_date"])[:10])
        if notes:
            label = key[6:] if key.startswith("motif:") else key
            out.append(_cand("vote_split", f"{label} ({chain[0]['motif']}): " + "; ".join(notes),
                             days=days, vote_ids=[v["id"] for v in chain]))
    return out
```

Ieliec `cands += _cands_vote_split(db, week_start, week_end)` `weekly_story_candidates` (secību nosaka `_STORY_KIND_ORDER`). Balsojuma vārdu (`Atturas`) raksti kā reģistrēts, nekad «balsoja pret» (CLAUDE.md § Abstention).

- [ ] **Step 4: Palaid** — `.venv/Scripts/python.exe -m pytest tests/test_weekly_story_candidates.py tests/test_briefs_weekly.py -q` → PASS (esošie `test_breakdown_*` pierāda, ka refaktorings izvadi nemainīja).

- [ ] **Step 5: Mutācija** — `SPLIT_MIN_MINORITY = 1` → `test_one_dissenter_is_not_a_split` krīt; izņem `_vote_mismatch` pārbaudi kandidātos → `test_mismatched_vote_is_skipped` krīt. Atjauno.

- [ ] **Step 6: Commit** — «Nedēļas stāsti: vote_split kandidāti; balsojumu dati kopīgi ar weekly_vote_breakdown».

---

### Task 3: `daily_lead` kandidāti

**Files:**
- Modify: `src/briefs.py`, `tests/test_weekly_story_candidates.py`

**Interfaces:**
- Consumes: `_cand()`, `brief_subject_date(topic, content, created_at)`.
- Produces: `_cands_daily_lead(db, week_start, week_end) -> list[dict]`.

**Noteikums (spec atstāja atvērtu, šeit fiksēts):** katrs dienas pārskata `## Galvenais` saraksta punkts, kas sākas ar `- **…**`, ir viens kandidāts; `fact` = treknais teksts, `days` = pārskata subjekta diena. Tēmu nosaka deterministiski: visas markdown saites punktā `](url)` → `claims` ar šo `source_url` un `claim_type='position'` (bez NEEDS_REVIEW) → biežākā `topic` (vienādos — alfabētiski pirmā); `claim_ids` = atrastās pozīcijas. `repeated=True` visiem punktiem, kuru tēma vadīja ≥2 dažādās dienās. Ja neviena saite neatbilst pozīcijai (piem., saīsināta saite), `topic=None`, `repeated=False` — aģents spriež pats. Katrai subjekta dienai ņem jaunāko (`MAX(id)`) dienas pārskatu.

- [ ] **Step 1: Krītošais tests**

```python
def test_daily_lead_marks_topic_that_led_two_days(tmp_path):
    from src.briefs import weekly_story_candidates
    db = _db(tmp_path)
    a = _claim(db, 1, "Valdības veidošana", "2026-05-26")
    b = _claim(db, 2, "Valdības veidošana", "2026-05-28")
    c = _claim(db, 1, "Budžets", "2026-05-28")
    def daily(day, bullets):
        body = f"# Dienas pārskats — {day}\n\n## Galvenais\n\n<!-- x -->\n\n" + "\n".join(bullets) + \
               "\n\n## Aktīvākie politiķi\n\n- **Nav šis** ([e](https://e.lv/x))\n"
        db.execute("INSERT INTO context_notes (opponent_id, note_type, topic, content, created_at) "
                   "VALUES (NULL, 'daily_brief', ?, ?, ?)", (f"dienas analīze {day}", body, f"{day} 21:00:00"))
    url = lambda cid: db.execute("SELECT source_url FROM claims WHERE id=?", (cid,)).fetchone()[0]
    daily("2026-05-26", [f"- **Kulbergs sola darba plānu.** Teksts ([e]({url(a)}))."])
    daily("2026-05-28", [f"- **Valdība vēl nav.** ([e]({url(b)}))", f"- **Budžets.** ([e]({url(c)}))"])
    daily("2026-05-20", ["- **Cita nedēļa.** x"])
    db.commit()
    got = _kinds(weekly_story_candidates(db, WEEK), "daily_lead")
    assert [g["fact"] for g in got] == ["Kulbergs sola darba plānu.", "Valdība vēl nav.", "Budžets."]
    assert [g["repeated"] for g in got] == [True, True, False]
    assert got[0]["topic"] == "Valdības veidošana" and got[0]["claim_ids"] == [a]
```

- [ ] **Step 2: Palaid** → FAIL.

- [ ] **Step 3: Implementē**

```python
_LEAD_RE = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*")
_MD_LINK_URL_RE = re.compile(r"\]\((https?://[^)\s]+)\)")


def _galvenais_section(content: str) -> list[str]:
    lines, inside = [], False
    for line in (content or "").splitlines():
        if line.strip() == "## Galvenais":
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside:
            lines.append(line)
    return lines


def _cands_daily_lead(db, week_start, week_end):
    latest: dict[str, tuple[int, str]] = {}
    for r in db.execute("SELECT id, topic, content, created_at FROM context_notes "
                        "WHERE note_type = 'daily_brief' ORDER BY id"):
        day = brief_subject_date(r["topic"], r["content"], r["created_at"])
        if day and week_start <= day <= week_end:
            latest[day] = (r["id"], r["content"])
    leads = []  # (day, fact, topic, claim_ids)
    for day in sorted(latest):
        for line in _galvenais_section(latest[day][1]):
            m = _LEAD_RE.match(line)
            if not m:
                continue
            urls = _MD_LINK_URL_RE.findall(line)
            rows = db.execute(
                f"SELECT c.id, c.topic FROM claims c WHERE c.source_url IN ({','.join('?' * len(urls))}) "
                f"AND c.claim_type = 'position' AND {_NOT_NEEDS_REVIEW_SQL} ORDER BY c.id",
                urls).fetchall() if urls else []
            counts: dict[str, int] = {}
            for r in rows:
                counts[r["topic"]] = counts.get(r["topic"], 0) + 1
            topic = min(counts, key=lambda t: (-counts[t], t)) if counts else None
            leads.append((day, m.group(1).strip(), topic, [r["id"] for r in rows]))
    topic_days: dict[str, set] = {}
    for day, _f, topic, _ids_ in leads:
        if topic:
            topic_days.setdefault(topic, set()).add(day)
    return [_cand("daily_lead", fact, topic=topic, days=[day], claim_ids=ids_,
                  repeated=bool(topic) and len(topic_days[topic]) >= 2)
            for day, fact, topic, ids_ in leads]
```

Pievieno `cands += _cands_daily_lead(db, week_start, week_end)` `weekly_story_candidates`. Pārbaudi, ka `re` jau importēts `src/briefs.py`.

- [ ] **Step 4: Palaid** — `.venv/Scripts/python.exe -m pytest tests/test_weekly_story_candidates.py -q` → PASS.
- [ ] **Step 5: Commit** — «Nedēļas stāsti: daily_lead kandidāti no dienas pārskatu «Galvenais»».

---

### Task 4: Jaunais `generate_weekly_brief()` skelets

**Files:**
- Modify: `src/briefs.py` (`generate_weekly_brief` ~1218–1498)
- Modify: `tests/test_briefs_weekly.py`, `tests/test_briefs.py`, `tests/test_weekly_story_candidates.py`

**Interfaces:**
- Consumes: `weekly_story_candidates()`.
- Produces: skelets šādā secībā (precīzi virsraksti — no tiem atkarīgs 5. uzdevuma validators un priekšskats):

```
# Nedēļas stāsti — {week_start} līdz {week_end}

<!-- STORY_CANDIDATES ({N}) — aģentam: izvēlies 3–5 stāstus, tad šo komentāru aizvāc.
- [kind] fact · tēma: T · dienas: D1, D2 · pozīcijas: 1, 2 · balsojumi: 3 · pretrunas: 4[ · atkārtojas]
-->

<!-- AGENT: 3–5 stāsti, katrs ar savu `## ` virsrakstu (kas ko izdarīja), 60–220 vārdi. Aizvāc šo komentāru. -->

## Īsumā

<!-- AGENT: 0–5 teikumi, katrs ar saiti; ja nav ko teikt, sadaļu dzēs. Aizvāc šo komentāru. -->

## Ko gaidīt

<!-- AGENT: tikai datēti notikumi ar nedēļas dienu un datumu; ja tādu nav, sadaļu dzēs. Aizvāc šo komentāru. -->

## Nedēļa skaitļos
<!-- WEEKLY_STATS: … -->            (nemainīts)

## Kas kustējās
<!-- WEEKLY_BLOC … -->  ![Kas kustējās](…)  *leģenda*  - **Vārds** (partija) — N (↑d)   (nemainīts)

<!-- AGENT: frakciju un balsojumu skaitļus ņem TIKAI no weekly_vote_breakdown(...) … -->   (nemainīts, tikai ja vote_count)

**Dienu pārskati:** …              (nemainīts)

## Vizuālais brief

<!-- AGENT: Tēma / Galvenā tēze / Skaitlis / Metaforas hint. Aizvāc šo komentāru. -->
```

Tukšie lauki kandidāta rindā izlaisti (nav «balsojumi: —»). `-->` jebkurā `fact` aizvieto ar `—>`. `N=0` → komentārs ar `(0)` un rindu «- kandidātu nav».

- [ ] **Step 1: Pārraksti/dzēs vecās formas testus** (spec § 1 «Izzūd» ir mutācijas pierādījums — šīs sadaļas skeletā vairs nav):
  - Dzēst `tests/test_briefs_weekly.py`: `test_weekly_rest_topics_line_lists_topics_outside_top4`, `test_weekly_rest_topics_names_topics_with_3plus`, `test_weekly_rest_topics_line_absent_when_nothing_left`, `test_weekly_pretrunas_only_with_confirmed_rows`, `test_weekly_pretrunas_cell_uses_excerpt` (`contradiction_excerpt` testi `test_contradiction_excerpt_*` paliek — funkciju lieto dienas pārskats).
  - Dzēst `tests/test_briefs.py`: `test_weekly_skeleton_carries_explainer_once` (bloku tabulas nedēļā vairs nav).
  - Pārrakstīt `test_weekly_skeleton_has_new_sections`: H1 `# Nedēļas stāsti — 2026-05-26 līdz 2026-06-01`; ir `<!-- STORY_CANDIDATES`, `## Īsumā`, `## Ko gaidīt`, `## Nedēļa skaitļos`, `positions=4`, `## Kas kustējās`, `## Vizuālais brief`; NAV `## Nedēļas stāsts`, `## Nedēļas galvenās tēmas`, `## Koalīcija vs Opozīcija`, `**Pārējās tēmas:**`.
  - `test_briefs.py::TestGenerateWeeklyBrief::test_contains_header` → `"Nedēļas stāsti"`; `test_empty_week` → `"## Īsumā"` un `"STORY_CANDIDATES (0)"`.
  - `test_briefs.py::test_weekly_pretrunas_table_lists_post_midnight_contradiction` → pārsauc par `..._candidates_list_post_midnight_contradiction`; asertē `contradictions=1 ` un ka kandidātu komentārā ir rinda `[contradiction]`.
  - `test_briefs.py` NEEDS_REVIEW weekly tests (~1491): aizvieto stance asertus ar: NEEDS_REVIEW pozīciju id neparādās `STORY_CANDIDATES` komentārā; `positions=2 ` un movers rinda paliek.
  - `test_weekly_skeleton_carries_previous_forward_look`: punkti tagad ir `[followup]` rindas `STORY_CANDIDATES` komentārā; `-->` neaizver komentāru (komentārs beidzas tikai ar savu `-->` rindu); «nav šis», «Tēma», «Dienu pārskati» komentārā nav.
- [ ] **Step 2: Jauns tests** (`tests/test_weekly_story_candidates.py`):

```python
def test_skeleton_lists_candidates_and_defuses_comment_close(tmp_path):
    from src.briefs import generate_weekly_brief
    db = _surge_db(tmp_path, 8, 0)
    db.execute("UPDATE claims SET topic = 'Tēma --> x'")
    db.commit()
    path = db.execute("PRAGMA database_list").fetchone()[2]
    md = generate_weekly_brief(path, week_start=WEEK, chart_dir=str(tmp_path / "c"))
    start = md.index("<!-- STORY_CANDIDATES (")
    block = md[start:md.index("\n-->", start)]
    assert "[topic_surge] Tēma —> x: 8 pozīcijas" in block
    assert "-->" not in block


def test_skeleton_of_empty_week(tmp_path):
    from src.briefs import generate_weekly_brief
    db = _db(tmp_path)
    path = db.execute("PRAGMA database_list").fetchone()[2]
    md = generate_weekly_brief(path, week_start=WEEK, chart_dir=str(tmp_path / "c"))
    assert "<!-- STORY_CANDIDATES (0)" in md and "- kandidātu nav" in md
    assert "## Nedēļa skaitļos" in md
```

- [ ] **Step 3: Palaid** → jaunie un pārrakstītie testi FAIL.
- [ ] **Step 4: Implementē** — `generate_weekly_brief`: atstāj statistikas aprēķinus (`position_count`, `vote_count`, `contradiction_count`, `top_topic`, `top_party`), movers + `WEEKLY_BLOC` + SVG, balsojumu AGENT komentāru, `_weekly_day_links`. Dzēs: «Nedēļas stāsts» vietturi, pagājušās nedēļas AGENT komentāru (tagad followup kandidāti), tēmu sadaļas un «Pārējās tēmas», «Koalīcija vs Opozīcija» tabulu un `week_bloc_rows`, «Pretrunas» tabulu. Formatētājs:

```python
def _story_candidates_comment(cands: list[dict]) -> str:
    lines = [f"<!-- STORY_CANDIDATES ({len(cands)}) — aģentam: izvēlies 3–5 stāstus, "
             "tad šo komentāru aizvāc."]
    if not cands:
        lines.append("- kandidātu nav")
    for c in cands:
        parts = [f"- [{c['kind']}] {c['fact']}"]
        if c["topic"]:
            parts.append(f"tēma: {c['topic']}")
        for label, key in (("dienas", "days"), ("pozīcijas", "claim_ids"),
                           ("balsojumi", "vote_ids"), ("pretrunas", "contradiction_ids")):
            if c[key]:
                parts.append(f"{label}: {', '.join(map(str, c[key]))}")
        if c["repeated"]:
            parts.append("atkārtojas")
        lines.append(" · ".join(parts).replace("-->", "—>"))
    lines.append("-->")
    return "\n".join(lines) + "\n"
```

Pēc refaktoringa palaid `ruff check src/briefs.py` un izņem nelietotos importus/palīgus TIKAI tad, ja tos nelieto arī dienas pārskats (`_bloc_summary`, `BLOC_TABLE_EXPLAINER`, `contradiction_excerpt` dienas pusē paliek).
- [ ] **Step 5: Palaid** — `.venv/Scripts/python.exe -m pytest tests/test_weekly_story_candidates.py tests/test_briefs_weekly.py tests/test_briefs.py tests/test_render_weekly.py tests/test_generate.py -q` → PASS.
- [ ] **Step 6: Commit** — «Nedēļas stāsti: jaunais skelets (kandidāti, Īsumā, Ko gaidīt); vecās tēmu/bloku sadaļas izņemtas».

---

### Task 5: Validators, priekšskats, E2E

**Files:**
- Modify: `src/tools.py:253-266`, `src/render/blog.py:512-552`
- Modify: `tests/test_tools.py`, `tests/test_landing_preview_and_active.py`
- Create: `tests/test_weekly_stories_e2e.py`

**Interfaces:**
- Consumes: Task 4 skeleta virsraksti.
- Produces: `_validate_brief_structure(content, "weekly_brief")` pieņem jauno formu; `_brief_preview(body)` jaunajai formai ņem pirmā stāsta pirmo rindkopu.

**Validatora noteikumi (jaunā forma = nav `## Nedēļas stāsts`):** sākas ar `# `; nav `STORY_CANDIDATES` un nav `<!-- AGENT` (neaizpildīts skelets nedrīkst nonākt DB); ir `## Nedēļa skaitļos`; starp H1 un pirmo no (`## Īsumā`, `## Ko gaidīt`, `## Nedēļa skaitļos`) ir ≥3 `## ` virsraksti; garums ≥2 500 zīmes. Vecā forma (ir `## Nedēļas stāsts`) — tieši vecās pārbaudes, nemainītas.

- [ ] **Step 1: Krītošie testi**

`tests/test_tools.py` blakus esošajam weekly testam (vecais paliek nemainīts):

```python
def _new_weekly(stories=3, extra=""):
    body = "".join(f"## Stāsts {i}\n\n" + ("Otrdien Saeima pieņēma lēmumu. " * 30) + "\n\n"
                   for i in range(stories))
    return ("# Nedēļas stāsti — 2026-10-26 līdz 2026-11-01\n\n" + body + extra +
            "## Īsumā\n\n- x\n\n## Nedēļa skaitļos\n\n<!-- WEEKLY_STATS: positions=1 votes=0 "
            "contradictions=0 top_topic=A top_party=B -->\n\n## Vizuālais brief\n\n- **Tēma:** A\n")


def test_weekly_new_form_accepted_and_gated():
    from src.tools import _validate_brief_structure
    _validate_brief_structure(_new_weekly(), "weekly_brief")
    for bad, why in ((_new_weekly(stories=2), "stāst"),
                     (_new_weekly(extra="<!-- STORY_CANDIDATES (3)\n- x\n-->\n"), "STORY_CANDIDATES"),
                     (_new_weekly(extra="<!-- AGENT: x -->\n"), "AGENT"),
                     (_new_weekly().replace("## Nedēļa skaitļos", "## Cits"), "Nedēļa skaitļos")):
        with pytest.raises(ValueError) as e:
            _validate_brief_structure(bad, "weekly_brief")
        assert why in str(e.value)
```

`tests/test_landing_preview_and_active.py`:

```python
def test_new_weekly_preview_reads_first_story():
    body = ("<!-- c -->\n\n## Saeima atlika budžetu\n\nOtrdien Saeima atlika budžeta "
            "lasījumu ([lsm.lv](https://lsm.lv/a)).\n\n## Otrs stāsts\n\nCits.\n\n"
            "## Nedēļa skaitļos\n\n<!-- WEEKLY_STATS: positions=1 -->\n")
    assert _brief_preview(body).startswith("Otrdien Saeima atlika budžeta lasījumu")
```

`tests/test_weekly_stories_e2e.py` — viens E2E (spec § 5): testa DB ar frakcijas šķelšanos (Task 2 `_vote_db` forma) UN tēmas lēcienu (8 pozīcijas) → `generate_weekly_brief()` → komentārā ir gan `[vote_split]`, gan `[topic_surge]`; tad skeletu aizpilda ar paraugu (izdzēš `STORY_CANDIDATES` un `<!-- AGENT` komentārus, ieliek 3 stāstus kā `_new_weekly`) → `store_context_note(topic="nedēļas analīze 2026-05-25 līdz 2026-05-31", note_type="weekly_brief", content=md)` atgriež veiksmi pret testa DB (izmanto to pašu DB pārslēgšanas paņēmienu, ko `tests/test_tools.py` lieto `store_context_note` testos — grep `monkeypatch` tur) → `src.render.blog._weekly_content_for_render(md, is_weekly=True)` satur `weekly-stats` un nesatur `STORY_CANDIDATES`; `_brief_preview` (no satura bez H1) sākas ar pirmā stāsta tekstu. Palīgus `_db`/`_claim`/`_vote_db` importē no `tests.test_weekly_story_candidates` vai pārvieto uz kopīgu palīgu tajā pašā failā — nedublē.

- [ ] **Step 2: Palaid** → FAIL.
- [ ] **Step 3: Implementē**

`src/tools.py` weekly zars:

```python
    elif note_type == "weekly_brief":
        missing = []
        if not content.startswith("# "):
            missing.append("Jāsākas ar '# ' (H1, ne '##')")
        if "## Nedēļas stāsts" in content:  # vecā forma (līdz 2026-10-11) — UPSERT vecajiem
            if "## Nedēļas galvenās tēmas" not in content:
                missing.append("Trūkst sekcija: ## Nedēļas galvenās tēmas")
            if len(content) < 3000:
                missing.append(f"Pārāk īss: {len(content)} chars (min 3000)")
        else:  # «Nedēļas stāsti» (2026-11-01)
            for marker in ("STORY_CANDIDATES", "<!-- AGENT"):
                if marker in content:
                    missing.append(f"Skeleta komentārs nav aizvākts: {marker}")
            if "## Nedēļa skaitļos" not in content:
                missing.append("Trūkst sekcija: ## Nedēļa skaitļos")
            stop = min((content.find(h) for h in ("## Īsumā", "## Ko gaidīt", "## Nedēļa skaitļos")
                        if h in content), default=len(content))
            stories = [ln for ln in content[:stop].splitlines() if ln.startswith("## ")]
            if len(stories) < 3:
                missing.append(f"Par maz stāstu: {len(stories)} (min 3 `## ` virsraksti pirms «Īsumā»)")
            if len(content) < 2500:
                missing.append(f"Pārāk īss: {len(content)} chars (min 2500)")
        if missing:
            raise ValueError("Nedēļas pārskats neatbilst formāta prasībām:\n- " + "\n- ".join(missing))
```

Pārbaudi, ka vecā testa ziņa (`"Nedēļas stāsts" in str(e.value)` `test_tools.py:230`) joprojām izpildās: vecajā testā `## Nedēļas stāsts` aizvietots ar `## Kaut kas`, tāpēc tas ieies JAUNAJĀ zarā. Ja vecais tests krīt, pievieno jaunā zara kļūdai norādi «(vai vecā forma: ## Nedēļas stāsts + ## Nedēļas galvenās tēmas)», nevis maini veco testu.

`src/render/blog.py` `_brief_preview`: ja `galvenais_match` nav, meklē pirmo stāsta virsrakstu:

```python
    _NON_STORY = ("Nedēļa skaitļos", "Kas kustējās", "Vizuālais brief", "Īsumā", "Ko gaidīt")
    if not galvenais_match:
        galvenais_match = next(
            (m for m in re.finditer(r"(?m)^## (.+)\n", body) if m.group(1).strip() not in _NON_STORY),
            None)
```

(pirms `if galvenais_match:` bloka; pārējā loģika nemainās). Atjauno docstring.

- [ ] **Step 4: Palaid** — `.venv/Scripts/python.exe -m pytest tests/test_tools.py tests/test_landing_preview_and_active.py tests/test_weekly_stories_e2e.py tests/test_render_weekly.py tests/test_blog_brief_presentation.py -q` → PASS.
- [ ] **Step 5: Mutācija** — izņem `STORY_CANDIDATES` pārbaudi validatorā → `test_weekly_new_form_accepted_and_gated` krīt; atjauno.
- [ ] **Step 6: Commit** — «Nedēļas stāsti: validators un priekšskats jaunajai formai; E2E tests».

---

### Task 6: LV lint 7. likums `analytic-filler-iezime`

**Files:**
- Modify: `src/lv_style.py` (`RULES_TOTAL`, `lint_lv_style` pēc 6. likuma, moduļa docstring)
- Modify: `tests/test_lv_style.py` (rindas 158, 171, 421: `6` → `7`; jauni testi)

**Interfaces:** `lint_lv_style()` atgriež arī `{"rule": "analytic-filler-iezime", …}`.

**Tvērums:** proza bez tabulām, bez context-box (`_strip_protected_regions(content, protect_tables=True, protect_context_box=True)`), bez «…» citātiem (`re.sub(r"«[^»\n]*»", "", …)`), bez HTML komentāriem. Regex `\biezīm[ēe]\w*` ar `re.IGNORECASE`. Likums neprasa uzvārdu kopu (nekad nav `rules_skipped`).

- [ ] **Step 1: Krītošie testi**

```python
def test_rule7_flags_analytic_iezime():
    issues = lint_lv_style("Stendzenieks (LPV) iezīmē selektīvu darbaspēka imigrāciju.\n", surnames=set())
    assert [i["rule"] for i in issues] == ["analytic-filler-iezime"]


def test_rule7_ignores_quote_table_and_box():
    text = ('Ministrs teica: «Mēs iezīmējam robežu.»\n\n'
            "| a | iezīmē |\n|---|---|\n\n"
            '<div class="context-box" markdown="1">\nTendence iezīmējas.\n</div>\n')
    assert not [i for i in lint_lv_style(text, surnames=set()) if i["rule"] == "analytic-filler-iezime"]
```

Mutācija: izslēdz likumu (komentē cilpu) → `test_rule7_flags_analytic_iezime` krīt.

- [ ] **Step 2: Palaid** → FAIL. **Step 3:** implementē, `RULES_TOTAL = 7`, ieteikums: «Pasaki, ko politiķis izdarīja vai teica (saka, ierosina, atbalsta); «iezīmē» ir analītiķa pildvārds (spec 2026-11-01).» **Step 4:** `.venv/Scripts/python.exe -m pytest tests/test_lv_style.py -q` → PASS. **Step 5:** commit «LV lints: 7. likums «iezīmē» kā analītisks pildvārds».

---

### Task 7: Prompti, runbooks, CHANGELOG

**Files:**
- Modify: `.claude/agents/weekly-brief-writer.md` (pārrakstīt § Ievaddati, SAGLABĀ, PAPILDINI, Viens fakts, Valoda, Self-check; § Publicēšanas pauze, Storage, Izvietojums — paturēt), `.claude/agents/quality-reviewer.md` § H (weekly apakšpunkts), `wiki/operations/weekly-routine.md`, `wiki/CHANGELOG.md`, `.claude/agents/quality-reviewer.md:503` («sešus» → «septiņus»).

Saturs (no spec § 1 un § 3; nekopē spec pilnībā — saite uz to):
- **Ievaddati:** skelets + `STORY_CANDIDATES` komentārs; aģents lasa kandidātus un to `claim_ids`/`vote_ids`/`contradiction_ids` avotus pilnībā, ne visu nedēļu. Balsojumu skaitļi tikai no `weekly_vote_breakdown`.
- **Izvēle:** 3–5 stāsti; prioritāte pretruna/šķelšanās → `daily_lead` ar «atkārtojas» → `topic_surge` → spriedzes; ≤2 stāsti no vienas tēmas; ≥2 avoti/pozīcijas uz stāstu, viens tvīts nav stāsts; neizvēlēts → drīkst būt viens «Īsumā» teikums. Atskaitē «izskatīti N kandidāti, izvēlēti K» + viens iemesls katram noraidītajam.
- **Forma:** spec § 1 bloks (virsraksts = kas ko izdarīja, bez numura; 60–220 vārdi; sāk ar faktu un dienu; 0–2 citāti; maiņa → abi punkti ar datumiem; beidzas ar pēdējo konkrēto faktu). Mērķis kopā 700–1 000 vārdu; >1 000 = saīsini.
- **SAGLABĀ verbatim:** H1, `WEEKLY_STATS`, `## Kas kustējās` bloks ar `WEEKLY_BLOC`, grafiku, leģendu un movers rindām (tās ir vienīgā vieta, kur treknraksts atļauts), `**Dienu pārskati:**`. **Aizvāc** `STORY_CANDIDATES` un visus `<!-- AGENT` (validators citādi atsaka).
- **Aizliegtie rāmji** — spec § 3 tabula vienā sarakstā + strukturālie noteikumi + saskaņojumi (domuzīme, atrunas, «uzsver»). Treknraksts prozā — nekur.
- **Self-check:** `## ` stāstu skaits 3–5; vārdu skaits; `STORY_CANDIDATES`/`<!-- AGENT` = 0; `lint_lv_style == []` + `lint_lv_style_report` saucēji (`rules_run / rules_total` = 7/7); frakciju skaitļi pret `weekly_vote_breakdown`; «Ko gaidīt» punktiem diena + datums; `[x.com](` = 0; aizliegto rāmju skaits = 0; tokenu skaits atskaitē (spec § 7 mērījums).
- **Self-check «Dienu pārskati»/Pārējās tēmas/Koalīcija tabula** — izņemt no prompta (sadaļu vairs nav).
- **quality-reviewer § H** weekly: stāsta pēdējais teikums nav punkta atkārtojums; pirmais neatkārto virsrakstu; nav «kāpēc tas svarīgi» soļa; nav trīs paralēlu piemēru, kur pietiek ar diviem; «nav X, bet Y» mūsu tekstā; spriedums, ne regex.
- **weekly-routine.md:** pirmdienas rīts par iepriekšējo P–Sv; svētdien tikai dienas pārskats; jaunā struktūra 5 rindās; saite uz spec un šo plānu.
- **CHANGELOG.md** (≤5 rindas): «2026-11-0X — Nedēļas stāsti: pārskats = 3–5 stāsti no koda kandidātiem (`weekly_story_candidates`); tēmu/bloku/pretrunu sadaļas skeletā izņemtas; lint 7. likums «iezīmē» (attiecas arī uz dienas pārskatiem). Spec/plāns: docs/superpowers/…».

- [ ] **Step 1:** rediģē failus. **Step 2:** `bash scripts/check.sh` (ruff + pytest + render smoke) → zaļš; ja «os error 1455», `CHECK_PYTEST_WORKERS=3 bash scripts/check.sh`. **Step 3:** LV gramatikas pārbaude visam jaunajam tekstam promptos. **Step 4:** commit «Nedēļas stāsti: aģenta prompts, QR § H, nedēļas runbook, CHANGELOG».

---

## Pēc ieviešanas (orķestrators, ne palīgs)

1. Izlasīt pilnu diff (`git diff <sākuma commit>..HEAD`), nogriezt lieko.
2. `generate_weekly_brief(week_start="2026-10-26")` pret dzīvo DB (tikai lasīšana + SVG `output/`) — pārbaudīt, ka kandidātos ir spec mērījuma signāli (3 pretrunas, «Korupcija un KNAB» lēciens, Liepnieks→Kulbergs, 5 jaunas balsis) un saskaitīt kandidātus.
3. Pilots 10-26…11-01 — tikai ar operatora atļauju; tokenu mērījums pret 2026-10-11 pārskatu; publicēšana ar atsevišķu atļauju.
