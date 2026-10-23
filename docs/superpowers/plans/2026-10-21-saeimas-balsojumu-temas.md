# Saeimas balsojumu tēmas — īstenošanas plāns

> **Aģentiem:** obligātā apakšprasme — `superpowers:subagent-driven-development` (ieteicams) vai `superpowers:executing-plans`. Soļi ar `- [ ]` izsekošanai. Palīgi uz Opus (`model: 'opus'`); neviens palīgs neizpilda `git stash`, `git checkout --`, `git restore`, `git reset`. Vienmēr `.venv/Scripts/python.exe`, nekad kails `python`. `PYTHONUTF8=1`.

**Mērķis:** katram Saeimas balsojumam ir tēma, kas atbilst tā saturam; tēmu izlemj vienreiz katram dokumentam, un visi tā balsojumi to manto.

**Arhitektūra:** jauna lēmumu tabula `saeima_document_topics` (tikai pievieno) ir vienīgais tēmas avots. Klasifikatoru (atslēgvārdi / Jev / Claude) izvēlas mērījums uz zelta kopas. Esošās 8 407 balsojumu un ~686 000 ierakstu tēmas pārraksta iesaldētās partijās (~300 dokumentu), katrai — snapshot tabula + komitēts rollback PIRMS apply; stāvoklis dzīvo DB, tāpēc darbu var sadalīt pa sesijām.

**Tehnoloģijas:** Python 3.12, SQLite, pytest, TypeSafe System One (`src/typesafe_client.py`), Claude Opus apakšaģenti.

**Spec:** `docs/superpowers/specs/2026-10-21-saeimas-balsojumu-temas-design.md` (lasīt pirms jebkura uzdevuma).

## Global Constraints

- Kanonisko tēmu skaits kļūst **34**; jaunā tēma ir tieši `"Saeimas darbs"`.
- «Saeimas darbs» = tikai parlamenta iekšējā kārtība (sēdes sākšana/slēgšana, darba kārtības izmaiņas, deputātu pārcelšana komisijās, Saeimas amatpersonu ievēlēšana, klātbūtnes reģistrācija). Tiesneši, rezolūcijas, pieprasījumi, likumprojektu procedūras balsojumi — savā politikas tēmā. Balsojuma līmeņa procedūras atpazīšana paliek kā šodien no motīva (`is_urgency_declaration`, `_REFERRAL_CLAUSE_RE`, `_vote_salience`, veto `party_contradictions.py:139–145`); dokumenta lēmums ir TIKAI tēma.
- `vote_topic_snapshot` rindas nekad nedzēš: partiju rollback faili atjauno no tām (atšķirībā no citiem `data/rollback_*.sql` tie nav pašpietiekami).
- Tēmu uz `saeima_votes.topic` / `claims.topic` raksta TIKAI `src/saeima/topics.py` (ielādē un partijās). Neviena cita `UPDATE ... SET topic` jaunā kodā.
- Neviena datu partija netiek piemērota pirms 1. uzdevuma (0. fāze) ir masterā.
- Katram apply: `data/rollback_vote_topics_<batch_id>.sql` komitēts PIRMS apply (eskalācija 8); `saeima_vote` ierakstiem vektorus NEpārrēķina.
- Laika zīmogi jaunajās tabulās = UTC (`datetime('now')`), kā `src/saeima/schema.py` (komentārā to pasaka).
- Zelta kopas etiķetes, pašreizējās tēmas un strīdu lēmumi NEnonāk nevienā klasifikatora promptā.
- Jev modelis: glabā atbildes `model` lauku (atrisināto), nevis `jev-latest` (sal. `backlog/dati-db.md` § Jev keša atslēga).
- Latviešu teksti (rubrika, atskaites, CHANGELOG) — gramatikas + stilistikas vārti (CLAUDE.md § Output Conventions).

## Review Focus

1. **Atkārtota ielāde pēc partijas** — jau saglabāts balsojums ar pārrakstītu tēmu tiek ielādēts vēlreiz → nedrīkst rasties otrs ieraksts (1. uzdevums, tests `test_reingest_after_topic_change_creates_no_duplicate`).
2. **Partija apstājas pusē** (izņēmums starp `saeima_votes` un `claims` UPDATE) → nekas nav mainīts, statuss paliek `snapshotted` (3. uzdevums, `test_apply_is_atomic_on_failure`).
3. **Kāds cits mainījis tēmu starp snapshot un apply** (piem., ielāde vai roku labojums) → apply atsaka, nevis pārraksta (3. uzdevums, `test_apply_refuses_when_topic_drifted`).
4. **Neparasts `document_nr`** (`1179` bez sufiksa; motīvs ar vairākiem numuriem, piem., balsojums 3512 ar `123/Lp14`, `152/Lp14`, `158/Lm14`) → normalizē tikai, ja viennozīmīgi; citādi `multi` atslēga ar lēmumu tikai ar roku (2. un 8. uzdevums, `test_document_key_*`).
5. **Jev nav pieejams vai atgriež nezināmu etiķeti** → `review_status='pending'`, tēma no atslēgvārdiem, žurnāla ieraksts; nekad kluss «pārliecināts» rezultāts (6. un 8. uzdevums).

---

## Sesiju sadalījums

| Sesija | Uzdevumi | Iznākums | Vārti pirms nākamās |
|---|---|---|---|
| 1 | 1–3 | kods: 0. fāze, shēma + 34. tēma, partiju dzinējs | `bash scripts/check.sh` zaļš |
| 2 | 4–5 | zelta kopa iezīmēta (~250 dok.), rubrika | T16 zaru audits izdarīts |
| 3 | 6–7 | trīs klasifikatoru prognozes + salīdzinājuma atskaite | **operators izvēlas uzvarētāju** |
| 4 | 8 | ielāde lieto lēmumu tabulu | check.sh zaļš, viena dzīva ielāde bez kļūdām |
| 5 | 10 (1.–2. solis: `sync_bill_topics`) | likumu tēmas seko lēmumiem | tests zaļš |
| 6…N | 9 (atkārto) | 1–3 partijas sesijā (~9 partijas kopā) | katras partijas atskaite + rollback komitēts |
| pēdējā | 10 | `saeima_bills.topic`, dokumentācija | CHANGELOG ieraksts |

Sesijas sākumā: `.venv/Scripts/python.exe scripts/vote_topics.py status` parāda, kur apstājāmies.

---

### Task 1: 0. fāze — ierakstu ģenerēšana lasa saglabāto tēmu

**Files:**
- Modify: `src/saeima/votes.py:788-793` (`_summary_row` vaicājums) un `:815` (`topic = _motif_to_topic(...)`)
- Test: `tests/test_saeima.py` (jauna klase `TestClaimTopicFromStoredVote`)

**Interfaces:**
- Produces: `generate_claims_from_votes()` lieto `saeima_votes.topic` rindai `vote_db_id`; ja rindas nav (testos `vote_db_id=0`) — `_motif_to_topic(vote.motif)` kā līdz šim.

- [ ] **Step 1: Uzraksti krītošo testu**

```python
class TestClaimTopicFromStoredVote:
    """0. fāze (spec 2026-10-21 § Lēmumi 1): tēma nāk no saeima_votes, ne no motīva.

    Bez tā pēc partijas pārrakstīšanas atkārtota ielāde ievietotu OTRU ierakstu,
    jo store_claim idempotence ir (opponent_id, source_url, topic) — T2.
    """

    def _vote(self):
        return VoteResult(
            motif="Grozījumi Notariāta likumā (412/Lp14), 2.lasījums",
            date="2026-06-11", time="10:30",
            total_par=50, total_pret=30, total_atturas=5, total_nebalso=15,
            result="Pieņemts", url="/voting/topic-test",
            individual_votes=[IndividualVote(deputy_name="Test Deputāts",
                                             faction="JV", vote="Par", politician_id=1)],
        )

    def test_reingest_after_topic_change_creates_no_duplicate(self, saeima_db, monkeypatch):
        import src.db as db_mod
        monkeypatch.setattr(db_mod, "DB_PATH", saeima_db)
        monkeypatch.setattr(saeima_mod, "DB_PATH", saeima_db)
        vote = self._vote()
        vid = store_vote(vote, agenda_item_id=None, db_path=saeima_db)
        first = generate_claims_from_votes(vote, vid, db_path=saeima_db)
        assert len(first) == 1
        db = get_db(saeima_db)
        db.execute("UPDATE saeima_votes SET topic='Tieslietas' WHERE id=?", (vid,))
        db.execute("UPDATE claims SET topic='Tieslietas' WHERE id=?", (first[0],))
        db.commit()
        db.close()
        again = generate_claims_from_votes(vote, vid, db_path=saeima_db)
        db = get_db(saeima_db)
        n = db.execute("SELECT count(*) FROM claims WHERE claim_type='saeima_vote'").fetchone()[0]
        db.close()
        assert again == first
        assert n == 1

    def test_new_claim_uses_stored_topic(self, saeima_db, monkeypatch):
        import src.db as db_mod
        monkeypatch.setattr(db_mod, "DB_PATH", saeima_db)
        monkeypatch.setattr(saeima_mod, "DB_PATH", saeima_db)
        vote = self._vote()
        vid = store_vote(vote, agenda_item_id=None, db_path=saeima_db)
        db = get_db(saeima_db)
        db.execute("UPDATE saeima_votes SET topic='Tieslietas' WHERE id=?", (vid,))
        db.commit()
        db.close()
        ids = generate_claims_from_votes(vote, vid, db_path=saeima_db)
        db = get_db(saeima_db)
        topic = db.execute("SELECT topic FROM claims WHERE id=?", (ids[0],)).fetchone()[0]
        db.close()
        assert topic == "Tieslietas"
```

- [ ] **Step 2: Palaid — jākrīt**

Run: `.venv/Scripts/python.exe -m pytest tests/test_saeima.py::TestClaimTopicFromStoredVote -v`
Expected: FAIL — `n == 2` pirmajā, `topic == 'Valsts pārvalde'` (vai cita atslēgvārdu tēma) otrajā.

- [ ] **Step 3: Minimālā izmaiņa**

`_summary_row` vaicājumā lasi arī tēmu:

```python
    _summary_row = _db_check.execute(
        "SELECT summary, topic FROM saeima_votes WHERE id = ?", (vote_db_id,)
    ).fetchone()
```

Rindas `:815` vietā:

```python
    # Tēma nāk no saglabātā balsojuma (spec 2026-10-21 § Lēmumi 1): pēc partijas
    # pārrakstīšanas motīva pārrēķins dotu citu tēmu un store_claim idempotences
    # atslēga (opponent_id, source_url, topic) ievietotu otru ierakstu (T2).
    topic = (_summary_row["topic"] if _summary_row and _summary_row["topic"]
             else _motif_to_topic(vote.motif))
```

- [ ] **Step 4: Palaid testu + visu Saeimas komplektu**

Run: `.venv/Scripts/python.exe -m pytest tests/test_saeima.py tests/test_saeima_petitions.py -q`
Expected: PASS.

- [ ] **Step 5: Mutācijas pierādījums** — īslaicīgi atgriez `topic = _motif_to_topic(vote.motif)`, pārliecinies, ka abi jaunie testi krīt, atjauno.

- [ ] **Step 6: Commit** (ziņa caur failu, `git commit -F`): «0. fāze: balsojuma ieraksti lasa saglabāto tēmu (T2 pret pārklasifikāciju)».

---

### Task 2: Shēma, dokumenta atslēga un 34. tēma

**Files:**
- Modify: `src/saeima/schema.py` (jaunas tabulas `init_saeima_tables` skriptā)
- Create: `src/saeima/topics.py` (šajā uzdevumā tikai `document_key()` un konstantes)
- Modify: `src/topic_map.py` (`TOPIC_GROUPS["Saeimas darbs"]`), `src/render/_common/constants.py` (`TOPIC_COLORS`)
- Modify tests: `tests/test_audit_topic_canonical.py:132` (`33` → `34`), `tests/test_topic_map.py`, `tests/test_csp_readpath.py` (atrast, kur pieņemts 33)
- Test: `tests/test_saeima_topics.py` (jauns)

**Interfaces:**
- Produces: `document_key(document_nr: str | None, motif: str) -> tuple[str | None, str]` → `(key, reason)`; `key` ir `"NNN/LpNN"`-forma vai `"motif:<sha1[:12]>"` (bez numura vai `reason='multi'`); `None` tikai kailam numuram, ko motīvs neatrisina (`reason` saka kāpēc).
- Produces: tabulas `saeima_document_topics`, `vote_topic_batches`, `vote_topic_batch_members`, `vote_topic_snapshot` (DDL zemāk).
- Produces: `PROCEDURAL_TOPIC = "Saeimas darbs"`, `RUBRIC_VERSION = "2026-10-21.1"` no `src/saeima/topics.py`.

- [ ] **Step 1: Krītošie testi** (`tests/test_saeima_topics.py`)

```python
from src.saeima.topics import document_key


def test_document_key_keeps_canonical_form():
    assert document_key("412/Lp14", "Grozījumi Notariāta likumā (412/Lp14)")[0] == "412/Lp14"


def test_document_key_repairs_bare_number_from_motif():
    key, _ = document_key("1179", "Grozījumi … likumā (1179/Lp14), 1.lasījums")
    assert key == "1179/Lp14"


def test_document_key_ambiguous_motif_gets_own_key_and_flag():
    key, reason = document_key(None, "Par … (123/Lp14) un (152/Lp14) … (158/Lm14)")
    assert key.startswith("motif:") and reason == "multi"


def test_document_key_no_number_is_motif_hash():
    k1, _ = document_key(None, "Par sēdes sākšanu")
    k2, _ = document_key(None, "Par sēdes sākšanu")
    assert k1 == k2 and k1.startswith("motif:")


def test_saeimas_darbs_is_canonical():
    from src.topic_map import TOPIC_GROUPS, normalize_topic
    from src.render._common.constants import TOPIC_COLORS
    assert "Saeimas darbs" in TOPIC_GROUPS
    assert "Saeimas darbs" in TOPIC_COLORS
    assert normalize_topic("Saeimas darbs") == "Saeimas darbs"
```

- [ ] **Step 2: Palaid — jākrīt** (`ImportError` / `KeyError`).

- [ ] **Step 3: Implementācija**

`src/saeima/topics.py`:

```python
"""Saeimas balsojumu tēmas — vienīgais rakstītājs (spec 2026-10-21).

Lēmums tiek pieņemts dokumentam (`document_key`), balsojumi un to ieraksti to
manto. `saeima_votes.topic` / `claims.topic` (claim_type='saeima_vote') raksta
TIKAI šis modulis.
"""
from __future__ import annotations

import hashlib
import re

PROCEDURAL_TOPIC = "Saeimas darbs"
RUBRIC_VERSION = "2026-10-21.1"

_DOCNR_RE = re.compile(r"\b(\d+)/(Lp|Lm|P)(\d+)\b")
_CANON_RE = re.compile(r"^\d+/(Lp|Lm|P)\d+$")


def document_key(document_nr: str | None, motif: str) -> tuple[str | None, str]:
    """Normalizēta dokumenta atslēga balsojumam; None = kails numurs, ko motīvs neatrisina."""
    raw = (document_nr or "").strip()
    if _CANON_RE.match(raw):
        return raw, "canonical"
    found = {f"{n}/{k}{c}" for n, k, c in _DOCNR_RE.findall(motif or "")}
    if raw.isdigit():
        hits = [f for f in found if f.split("/")[0] == raw]
        if len(hits) == 1:
            return hits[0], "bare-number-repaired"
        return None, f"kails numurs {raw}: motīvā {len(hits)} atbilstības"
    if len(found) == 1:
        return found.pop(), "from-motif"
    digest = hashlib.sha1((motif or "").strip().encode("utf-8")).hexdigest()[:12]
    if len(found) > 1:
        # Vairāki numuri (piem. balsojums 3512): savs atslēgas, bet lēmums tikai
        # ar roku — `reason='multi'` liek klasifikatoram atteikties (8. uzd.).
        return f"motif:{digest}", "multi"
    return f"motif:{digest}", "no-number"
```

`src/saeima/schema.py` — pievieno `init_saeima_tables` skriptam:

```sql
        -- Laika zona: decided_at/created_at/applied_at = UTC (datetime('now')).
        -- Spec 2026-10-21: tikai pievieno; aktuālais lēmums = lielākais id
        -- dokumentam ar review_status != 'rejected'.
        CREATE TABLE IF NOT EXISTS saeima_document_topics (
            id INTEGER PRIMARY KEY,
            document_key TEXT NOT NULL,
            document_nr_raw TEXT,
            topic TEXT NOT NULL,
            method TEXT NOT NULL CHECK (method IN ('keyword','jev','claude','human')),
            model TEXT,
            confidence REAL,
            input_hash TEXT NOT NULL,
            rubric_version TEXT NOT NULL,
            review_status TEXT NOT NULL DEFAULT 'auto'
                CHECK (review_status IN ('auto','pending','confirmed','rejected')),
            decided_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_sdt_key ON saeima_document_topics(document_key, id);

        CREATE TABLE IF NOT EXISTS vote_topic_batches (
            batch_id TEXT PRIMARY KEY,
            status TEXT NOT NULL CHECK (status IN
                ('planned','snapshotted','applied','rolled_back')),
            rollback_file TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            applied_at TEXT
        );
        CREATE TABLE IF NOT EXISTS vote_topic_batch_members (
            batch_id TEXT NOT NULL REFERENCES vote_topic_batches(batch_id),
            document_key TEXT NOT NULL,
            vote_id INTEGER NOT NULL,
            PRIMARY KEY (batch_id, vote_id)
        );
        CREATE TABLE IF NOT EXISTS vote_topic_snapshot (
            batch_id TEXT NOT NULL,
            table_name TEXT NOT NULL CHECK (table_name IN ('saeima_votes','claims')),
            row_id INTEGER NOT NULL,
            old_topic TEXT,
            new_topic TEXT NOT NULL,
            PRIMARY KEY (batch_id, table_name, row_id)
        );
```

`src/topic_map.py` → `TOPIC_GROUPS`:

```python
    # 2026-10-21 — 34. kanoniskā tēma (spec saeimas-balsojumu-temas): tikai
    # parlamenta iekšējā kārtība. Likumprojektu procedūras balsojumi NAV šeit —
    # tie paliek likuma tēmā (procedūru atpazīst motīvs, src/saeima/claims.py).
    "Saeimas darbs": [
        "saeimas darbs",
        "saeimas procedūra",
        "sēdes kārtība",
    ],
```

`TOPIC_COLORS`: `"Saeimas darbs": "#7d8597",   # neitrāli pelēkzils; nav partiju paletē, atšķiras no Valsts pārvalde #64748b`. Pirms commit pārbaudi pret `parties.color` (`SELECT color FROM parties`) UN pret blakus tēmām (Pilsētvide `#708090`, Valsts pārvalde `#64748b`) — ja tuvu, izvēlies citu.

Atjauno `33` → `34` testos un komentāros (`grep -rn "33 canonical\|33 kanonisk\|== 33" src tests`); CLAUDE.md teksts mainās 10. uzdevumā.

- [ ] **Step 4: Palaid** `.venv/Scripts/python.exe -m pytest tests/test_saeima_topics.py tests/test_topic_map.py tests/test_audit_topic_canonical.py tests/test_csp_readpath.py -q` → PASS.

- [ ] **Step 5: Atslēgas pārbaude pret dzīvo DB (tikai lasot)** — skripts `.scratch/doc_key_check.py`: katram `saeima_votes` `document_key(document_nr, motif)`; izdrukā skaitu pa `reason` un visas `multi`/`None` rindas. Gaidāms (plāna sausais skrējiens 2026-10-21): `canonical` 7 568, `no-number` 697, `from-motif` 113, `bare-number-repaired` 24, `multi` 5 — 2 715 atslēgas. `multi` rindas (vairāku likumprojektu termiņu pagarināšana u. tml.) izšķir tikai ar roku `decide`. Izdrukā arī dažādo `motif:` atslēgu skaitu starp 697 (tik roku/likumu lēmumu prasa josla bez numura). Skaitus ieraksti commit ziņā.

- [ ] **Step 6: Commit** «Shēma + document_key + 34. tēma «Saeimas darbs»».

---

### Task 3: Partiju dzinējs (freeze → snapshot → rollback fails → apply)

**Files:**
- Modify: `src/saeima/topics.py`
- Create: `scripts/vote_topics.py` (CLI: `status`, `decide`, `freeze`, `apply`, `rollback`)
- Test: `tests/test_saeima_topics.py`

**Interfaces:**
- Consumes: `document_key()`, tabulas no 2. uzdevuma.
- Produces:
  - `record_decision(db, key, topic, *, method, model, confidence, input_hash, review_status='auto', document_nr_raw=None) -> int` — validē `topic in TOPIC_GROUPS`, citādi `ValueError`.
  - `current_decision(db, key) -> sqlite3.Row | None`
  - `freeze_batch(db, batch_id, keys: list[str]) -> dict` — ieraksta dalībniekus (visi balsojumi ar šo atslēgu) un snapshot (`old_topic` = tagadējā, `new_topic` = `current_decision`); statuss `snapshotted`. Atslēgas bez lēmuma → `ValueError`.
  - `write_rollback_sql(db, batch_id, path) -> Path`
  - `apply_batch(db, batch_id, *, require_tracked=True) -> dict` — atgriež `{"votes": n, "claims": m, "before": {...}, "after": {...}, "collisions": 0}`.
  - `rollback_batch(db, batch_id) -> dict`

- [ ] **Step 1: Krītošie e2e testi** (pagaidu DB, kā `saeima_db` fikstūra; divi balsojumi, trīs ieraksti)

```python
def test_apply_rewrites_votes_and_claims_and_rolls_back(topics_db, tmp_path):
    db = get_db(topics_db)
    record_decision(db, "412/Lp14", "Tieslietas", method="human", model=None,
                    confidence=1.0, input_hash="h")
    freeze_batch(db, "b01", ["412/Lp14"])
    write_rollback_sql(db, "b01", tmp_path / "rb.sql")
    report = apply_batch(db, "b01", require_tracked=False)
    assert report["votes"] == 2 and report["claims"] == 3
    assert {r[0] for r in db.execute("SELECT topic FROM claims")} == {"Tieslietas"}
    db.executescript((tmp_path / "rb.sql").read_text(encoding="utf-8"))
    assert {r[0] for r in db.execute("SELECT topic FROM claims")} == {"Valsts pārvalde"}
    assert db.execute("SELECT status FROM vote_topic_batches").fetchone()[0] == "rolled_back"


def test_apply_refuses_when_topic_drifted(topics_db, tmp_path):
    db = get_db(topics_db)
    record_decision(db, "412/Lp14", "Tieslietas", method="human", model=None,
                    confidence=1.0, input_hash="h")
    freeze_batch(db, "b01", ["412/Lp14"])
    write_rollback_sql(db, "b01", tmp_path / "rb.sql")
    db.execute("UPDATE saeima_votes SET topic='Vide' WHERE id=1")
    with pytest.raises(RuntimeError, match="drift"):
        apply_batch(db, "b01", require_tracked=False)
    assert db.execute("SELECT status FROM vote_topic_batches").fetchone()[0] == "snapshotted"


def test_apply_is_atomic_on_failure(topics_db, tmp_path, monkeypatch):
    db = get_db(topics_db)
    record_decision(db, "412/Lp14", "Tieslietas", method="human", model=None,
                    confidence=1.0, input_hash="h")
    freeze_batch(db, "b01", ["412/Lp14"])
    write_rollback_sql(db, "b01", tmp_path / "rb.sql")
    import src.saeima.topics as t
    monkeypatch.setattr(t, "_update_claims", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError, match="boom"):
        apply_batch(db, "b01", require_tracked=False)
    assert {r[0] for r in db.execute("SELECT topic FROM saeima_votes")} == {"Valsts pārvalde"}


def test_apply_requires_committed_rollback(topics_db, tmp_path):
    db = get_db(topics_db)
    record_decision(db, "412/Lp14", "Tieslietas", method="human", model=None,
                    confidence=1.0, input_hash="h")
    freeze_batch(db, "b01", ["412/Lp14"])
    write_rollback_sql(db, "b01", tmp_path / "rb.sql")
    with pytest.raises(RuntimeError, match="nav komitēts"):
        apply_batch(db, "b01", require_tracked=True)


def test_record_decision_rejects_unknown_topic(topics_db):
    with pytest.raises(ValueError):
        record_decision(get_db(topics_db), "412/Lp14", "Nav tēma", method="jev",
                        model="jev-x", confidence=0.9, input_hash="h")
```

Fikstūra `topics_db`: `init_db` + `init_saeima_tables`, politiķi 1 un 2, divi balsojumi ar `document_nr='412/Lp14'`, `topic='Valsts pārvalde'`, url `u1`/`u2`; ieraksti: (1,u1), (2,u1), (1,u2), visi `claim_type='saeima_vote'`, `topic='Valsts pārvalde'` — caur `store_claim()`.

- [ ] **Step 2: Palaid — jākrīt** (`ImportError`).

- [ ] **Step 3: Implementācija** (`src/saeima/topics.py`)

```python
import subprocess
from pathlib import Path

from src.topic_map import TOPIC_GROUPS


def record_decision(db, key, topic, *, method, model, confidence, input_hash,
                    review_status="auto", document_nr_raw=None):
    if topic not in TOPIC_GROUPS:
        raise ValueError(f"nekanoniska tēma: {topic!r}")
    cur = db.execute(
        "INSERT INTO saeima_document_topics (document_key, document_nr_raw, topic,"
        " method, model, confidence, input_hash, rubric_version,"
        " review_status) VALUES (?,?,?,?,?,?,?,?,?)",
        (key, document_nr_raw, topic, method, model,
         confidence, input_hash, RUBRIC_VERSION, review_status))
    return cur.lastrowid


def current_decision(db, key):
    return db.execute(
        "SELECT * FROM saeima_document_topics WHERE document_key=? AND "
        "review_status != 'rejected' ORDER BY id DESC LIMIT 1", (key,)).fetchone()


def _votes_for_keys(db, keys):
    wanted = set(keys)
    out = []
    for vid, nr, motif in db.execute("SELECT id, document_nr, motif FROM saeima_votes"):
        k, _ = document_key(nr, motif)
        if k in wanted:
            out.append((k, vid))
    return out


def freeze_batch(db, batch_id, keys):
    decisions = {}
    for k in keys:
        d = current_decision(db, k)
        if d is None:
            raise ValueError(f"nav lēmuma: {k}")
        decisions[k] = d["topic"]
    members = _votes_for_keys(db, keys)
    with db:
        db.execute("INSERT INTO vote_topic_batches (batch_id, status) VALUES (?, 'snapshotted')",
                   (batch_id,))
        for k, vid in members:
            db.execute("INSERT INTO vote_topic_batch_members VALUES (?,?,?)", (batch_id, k, vid))
            old, url = db.execute("SELECT topic, url FROM saeima_votes WHERE id=?", (vid,)).fetchone()
            db.execute("INSERT INTO vote_topic_snapshot VALUES (?,?,?,?,?)",
                       (batch_id, "saeima_votes", vid, old, decisions[k]))
            for cid, ctopic in db.execute(
                    "SELECT id, topic FROM claims WHERE claim_type='saeima_vote' AND source_url=?",
                    (url,)).fetchall():
                db.execute("INSERT INTO vote_topic_snapshot VALUES (?,?,?,?,?)",
                           (batch_id, "claims", cid, ctopic, decisions[k]))
    return {"members": len(members)}


def write_rollback_sql(db, batch_id, path):
    path = Path(path)
    b = batch_id.replace("'", "''")
    path.write_text(f"""-- Rollback: vote topic batch {batch_id}
-- Forward: scripts/vote_topics.py apply {batch_id} (spec 2026-10-21-saeimas-balsojumu-temas)
-- ATKARĪBA: atjauno no vote_topic_snapshot (batch_id šis) — tās rindas nedrīkst dzēst.
-- Drošs atkārtot.
BEGIN;
UPDATE saeima_votes SET topic = (SELECT old_topic FROM vote_topic_snapshot s
  WHERE s.batch_id='{b}' AND s.table_name='saeima_votes' AND s.row_id=saeima_votes.id)
WHERE id IN (SELECT row_id FROM vote_topic_snapshot WHERE batch_id='{b}' AND table_name='saeima_votes');
UPDATE claims SET topic = (SELECT old_topic FROM vote_topic_snapshot s
  WHERE s.batch_id='{b}' AND s.table_name='claims' AND s.row_id=claims.id)
WHERE id IN (SELECT row_id FROM vote_topic_snapshot WHERE batch_id='{b}' AND table_name='claims');
UPDATE vote_topic_batches SET status='rolled_back' WHERE batch_id='{b}';
COMMIT;
""", encoding="utf-8")
    db.execute("UPDATE vote_topic_batches SET rollback_file=? WHERE batch_id=?",
               (str(path), batch_id))
    db.commit()
    return path


def _is_tracked(path):
    r = subprocess.run(["git", "ls-files", "--error-unmatch", str(path)],
                       capture_output=True)
    return r.returncode == 0 and not subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", str(path)]).returncode


def _distribution(db, batch_id, table):
    return dict(db.execute(
        f"SELECT t.topic, count(*) FROM {table} t JOIN vote_topic_snapshot s "
        "ON s.row_id=t.id AND s.table_name=? AND s.batch_id=? GROUP BY t.topic",
        (table, batch_id)).fetchall())


def _update_rows(db, batch_id, table):
    rows = db.execute("SELECT row_id, old_topic, new_topic FROM vote_topic_snapshot "
                      "WHERE batch_id=? AND table_name=?", (batch_id, table)).fetchall()
    n = 0
    for rid, old, new in rows:
        cur = db.execute(f"UPDATE {table} SET topic=? WHERE id=? AND topic IS ?", (new, rid, old))
        if cur.rowcount != 1:
            raise RuntimeError(f"drift: {table}.id={rid} vairs nav {old!r}")
        n += 1
    return n


def _update_claims(db, batch_id):
    return _update_rows(db, batch_id, "claims")


def apply_batch(db, batch_id, *, require_tracked=True):
    status, rb = db.execute("SELECT status, rollback_file FROM vote_topic_batches "
                            "WHERE batch_id=?", (batch_id,)).fetchone()
    if status != "snapshotted":
        raise RuntimeError(f"partija {batch_id} ir {status}, nevar piemērot")
    if require_tracked and (not rb or not _is_tracked(rb)):
        raise RuntimeError(f"rollback {rb} nav komitēts — eskalācija 8")
    collisions = db.execute("""
        SELECT count(*) FROM vote_topic_snapshot s JOIN claims c ON c.id=s.row_id
        JOIN claims o ON o.opponent_id=c.opponent_id AND o.source_url=c.source_url
             AND o.topic=s.new_topic AND o.id != c.id
        WHERE s.batch_id=? AND s.table_name='claims'""", (batch_id,)).fetchone()[0]
    if collisions:
        raise RuntimeError(f"{collisions} idempotences sadursmes — STOP")
    before = {t: _distribution(db, batch_id, t) for t in ("saeima_votes", "claims")}
    try:
        db.execute("BEGIN")
        votes = _update_rows(db, batch_id, "saeima_votes")
        claims = _update_claims(db, batch_id)
        db.execute("UPDATE vote_topic_batches SET status='applied', applied_at=datetime('now') "
                   "WHERE batch_id=?", (batch_id,))
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    after = {t: _distribution(db, batch_id, t) for t in ("saeima_votes", "claims")}
    parity = db.execute("""SELECT count(*) FROM claims c JOIN saeima_votes v ON v.url=c.source_url
        WHERE c.claim_type='saeima_vote' AND c.topic != v.topic""").fetchone()[0]
    return {"votes": votes, "claims": claims, "before": before, "after": after,
            "collisions": 0, "parity_mismatch": parity}
```

Piezīme izpildītājam: `get_db()` var atvērt savienojumu ar `isolation_level`, kas pats sāk transakcijas — pirms `db.execute("BEGIN")` pārbaudi `src/db.py::get_db` un, ja vajag, lieto `db.isolation_level = None` šīs funkcijas laikā. Testi `test_apply_is_atomic_on_failure` to pierāda.

`rollback_batch(db, batch_id)` = `db.executescript(Path(rb).read_text(encoding="utf-8"))` + atgriež skaitus.

`scripts/vote_topics.py` (argparse, `PRODUCTION_DB_PATH` pēc noklusējuma, `--db` testiem):
- `status` — partijas pa statusiem; dokumenti ar/bez lēmuma; `pending` skaits.
- `freeze <batch_id> --keys-file f.txt` — izdrukā dalībnieku un snapshot skaitus; uzraksta `data/rollback_vote_topics_<batch_id>.sql`.
- `apply <batch_id>` — izdrukā atskaiti JSON; `parity_mismatch != 0` → izeja 1.
- `rollback <batch_id>`.
- `decide <key> <topic> [--method human] [--note …]` — `record_decision(..., method='human', confidence=1.0, review_status='confirmed', input_hash=<no sample.csv vai 'manual'>)`; nekanoniska tēma → izeja 1.

- [ ] **Step 4: Palaid** `.venv/Scripts/python.exe -m pytest tests/test_saeima_topics.py -q` → PASS. Mutācija: noņem `AND topic IS ?` no `_update_rows` → `test_apply_refuses_when_topic_drifted` krīt; atjauno.

- [ ] **Step 5: Ātrdarbība uz kopijas** — nokopē DB uz `E:/atmina/.scratch/` (ne C:), ieraksti 300 `human` lēmumus ar pašreizējo tēmu+«Saeimas darbs» testam, `freeze` + `apply --db kopija`; izmēri laiku. Ja >5 min — pārej uz `executemany` ar pagaidu tabulu, tad atkārto testus.

- [ ] **Step 6: `bash scripts/check.sh`** → zaļš. **Commit** «Partiju dzinējs vote_topics: freeze/snapshot/rollback/apply».

---

### Task 4: Rubrika un zelta kopas izlase

**Files:**
- Create: `data/saeima_topic_gold/RUBRIKA.md`
- Create: `scripts/vote_topic_gold_sample.py`
- Create (ģenerēts, komitēts): `data/saeima_topic_gold/sample.csv`

**Interfaces:**
- Produces: `sample.csv` kolonnas `document_key, prefix, n_votes, current_topic, stratum, split, input_text, input_hash` (`current_topic` TIKAI izlases stratifikācijai; klasifikatoriem netiek padots). `input_text` = virsraksts (pirmā motīva daļa līdz numuram) + atšķirīgie `summary` (līdz 3, katrs ≤600 zīmes) + `saeima_bills.title/summary`, ja ir. `input_hash = sha1(input_text)`.

- [ ] **Step 1: RUBRIKA.md** — katrai no 34 tēmām: 1 rinda «ietver», 1 rinda «neietver → kur iet», 1–2 robežgadījumi no dzīvās DB (ar `document_nr`). Obligātās robežas: Vide/Klimats/Degviela (dabasgāze!), Valsts pārvalde/Saeimas darbs, Tieslietas/Korupcija, Sociālā/Pensijas/Veselība, Imigrācija/pilsonība, Koalīcija/Vēlēšanas (partiju finansēšana), Pašvaldības/Pilsētvide. Atsevišķi: likumprojekta procedūras balsojumi (steidzamība, nodošana komisijai, priekšlikumu termiņš, otrreizēja caurlūkošana) pieder likuma tēmai, NE «Saeimas darbs». Gramatikas vārti.

- [ ] **Step 2: Izlases skripts** — deterministisks (`random.Random(20261021)`), ~250 atslēgas:
  - visi dokumenti tēmās ar <15 dokumentiem;
  - 70 no «Valsts pārvalde», 25 no «Vide»;
  - katram prefiksam (`Lp`, `Lm`, `P`) vismaz 20;
  - 20 garās ķēdes (≥10 balsojumu) → `stratum='chain'` (šīm 5. uzdevumā etiķete arī katram balsojumam);
  - 20 `motif:` atslēgas (bez numura);
  - pārējais — proporcionāli.
  `split`: `dev`/`test` 40/60, grupējot pēc bāzes likuma nosaukuma (teksts pēc «Grozījumi» līdz numuram), lai viena likuma grozījumi nav abās pusēs.

- [ ] **Step 3: Palaid, pārbaudi skaitus** (izdrukā pa `stratum`, `prefix`, `split`), commit `sample.csv` + `RUBRIKA.md` + skripts.

---

### Task 5: Zelta etiķetes (sesija 2; atsākams)

**Files:**
- Create: `data/saeima_topic_gold/labels.csv` (`document_key, gold_topic, labeller, note`)
- Create: `data/saeima_topic_gold/chain_labels.csv` (`vote_id, document_key, gold_topic`)
- Create: `data/saeima_topic_gold/AUDITS.md`

- [ ] **Step 1: Pirmais marķētājs** — Claude šajā sesijā, partijās pa 50 rindām no `sample.csv`, pēc `RUBRIKA.md`, lasot `input_text` un vajadzības gadījumā `document_url`. Pēc katrām 50 — commit (atsākšana = nākamās neiezīmētās rindas). Pašreizējo tēmu NEskatīties (kolonnu nelasīt).
- [ ] **Step 2: Ķēžu etiķetes** — 20 `chain` dokumentiem katram balsojumam; izrēķini vote≠document īpatsvaru → ieraksti `AUDITS.md`. **Lēmums:** ≤5 % → izņēmumi tikai pārbaudes sarakstā (spec § Lēmumi 2); >5 % → pirms 9. uzdevuma pievieno `saeima_vote_topic_overrides` (atsevišķs mazs uzdevums ar savu testu) un ziņo operatoram.
  *(4. uzd. piezīme)* Īpatsvaru ziņo trijos veidos: katram dokumentam, kopā un kopā bez budžeta ķēdēm (1130/Lp14 — 195, 152/Lp14 — 175 balsojumi), lai divas ķēdes neizšķir 5 % slieksni.
- [ ] **Step 3: Otrs neatkarīgs marķētājs** — 60 rindu apakškopa (`split='test'`, nejauša), cits modelis (GPT-6-Astra caur `delegate_task`, tikai lasīšana, tikai `input_text` + `RUBRIKA.md`). Sakritība + katras nesakritības izšķiršana pret avotu → `AUDITS.md`.
- [ ] **Step 4: T16 zaru audits** — katrai tēmai un «Saeimas darbs» robežai nolasi 3 etiķetes pret avota tekstu (ne pret marķētāju sakritību). Rubrikas defekts → labo `RUBRIKA.md`, paaugstini `RUBRIC_VERSION`, pārmarķē skartās rindas. Ieraksti saucējus `AUDITS.md`.
- [ ] **Step 5: Commit** «Zelta kopa: N etiķetes, rubrika v…».

---

### Task 6: Klasifikatori

**Files:**
- Create: `src/saeima/topic_classifiers.py`
- Modify: `src/typesafe_client.py` tikai, ja vajag (piem., `timeout`)
- Test: `tests/test_saeima_topic_classifiers.py`
- Create: `data/saeima_topic_gold/pred_{keyword,stored,jev,claude}.csv` (`document_key, topic, confidence, model`)

**Interfaces:**
- Produces: `classify_keyword(input_text: str, motif: str) -> Prediction`; `classify_jev(rows: list[dict]) -> list[Prediction | None]`; `Prediction = NamedTuple(topic: str, confidence: float | None, model: str | None)`.

- [ ] **Step 1: Jev līgums** — izlasi `https://docs.typesafe.ai/api.md` (caur `web-fetch` aģentu) un `typesafe:typesafe-ai` skill; pieraksti precīzu `choice` jautājuma formu un atbildes lauku (`choice`, `confidence`, `probabilities`, modelis) faila docstringā. Saglabā vienu reālu atbildi kā `tests/fixtures/jev_choice_response.json` (bez atslēgas).
- [ ] **Step 2: Krītošie testi** (pret fikstūru, bez tīkla):

```python
def test_jev_choice_parses_fixture(monkeypatch):
    resp = json.loads(Path("tests/fixtures/jev_choice_response.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(tc, "system_one", lambda *a, **k: resp)
    preds = tc.classify_jev([{"document_key": "412/Lp14", "input_text": "Notariāta likums"}])
    assert preds[0].topic in TOPIC_GROUPS and 0 <= preds[0].confidence <= 1
    assert preds[0].model and preds[0].model != "jev-latest"


def test_jev_unknown_label_is_none(monkeypatch):
    monkeypatch.setattr(tc, "system_one", lambda *a, **k: {"answers": {"q0": {"choice": "Nav"}}})
    assert tc.classify_jev([{"document_key": "k", "input_text": "x"}]) == [None]


def test_jev_unavailable_is_none(monkeypatch):
    def boom(*a, **k):
        raise TypeSafeUnavailable("down")
    monkeypatch.setattr(tc, "system_one", boom)
    assert tc.classify_jev([{"document_key": "k", "input_text": "x"}]) == [None]
```

(Atbildes atslēgu nosaukumus `answers`/`q0` pielāgo 1. solī atrastajam līgumam — testa un koda formai jāsakrīt ar fikstūru.)

- [ ] **Step 3: Implementācija** — `classify_keyword` ietin `_map_motif_text` + `normalize_topic`. `classify_jev`: viens `choice` jautājums ar 35 opcijām (nosaukums → «ietver» rinda no RUBRIKA); pakete ≤40 rindu; kešs pēc `input_hash + RUBRIC_VERSION + atbildes model`; nezināma etiķete vai `TypeSafeUnavailable` → `None` un `log.warning`. RUBRIKA ielādē pārbauda, ka tās `RUBRIC_VERSION:` rinda = `topics.RUBRIC_VERSION` (citādi kļūda).
- [ ] **Step 4: Testi PASS; commit.**
- [ ] **Step 5: Prognozes visai `sample.csv`:**
  - `pred_keyword.csv` (šodienas kods) un `pred_stored.csv` (saglabātā `saeima_votes.topic`, vairākuma balss dokumentā);
  - `pred_jev.csv` — izdrukā `JevStats.summary()` (tokeni, cena);
  - `pred_claude.csv` — Opus apakšaģenti (`model: 'opus'`), katram 50 rindas, prompts = RUBRIKA + `document_key` + `input_text` (BEZ `current_topic`, BEZ etiķetēm), izvade JSON rindas `{document_key, topic, confidence}`; galvenā sesija validē, ka katra tēma ir kanoniska un rindu skaits = ievades skaits. Paziņo operatoram aģentu skaitu (~5).
- [ ] **Step 6: Commit prognozes.**

---

### Task 7: Salīdzinājuma atskaite un operatora izvēle

**Files:**
- Create: `scripts/eval_vote_topics.py`
- Test: `tests/test_eval_vote_topics.py` (tīrā metriku loģika — atļauts vienības tests)
- Create: `data/saeima_topic_gold/ATSKAITE.md`

- [ ] **Step 1: Krītošais metriku tests**

```python
from scripts.eval_vote_topics import metrics

def test_metrics_counts_and_macro_f1():
    gold = {"a": "X", "b": "X", "c": "Y"}
    pred = {"a": "X", "b": "Y", "c": "Y"}
    weights = {"a": 1, "b": 1, "c": 10}
    m = metrics(gold, pred, weights)
    assert m["n"] == 3 and m["acc_doc"] == 2 / 3
    assert m["acc_vote"] == 11 / 12
    assert round(m["macro_f1"], 3) == round((2 / 3 + 2 / 3) / 2, 3)
    assert m["support"] == {"X": 2, "Y": 1}


def test_metrics_missing_prediction_counts_as_abstain():
    m = metrics({"a": "X"}, {}, {"a": 1})
    assert m["abstain"] == 1 and m["acc_doc"] == 0
```

- [ ] **Step 2: Implementē** `metrics(gold, pred, weights) -> dict` (`n`, `acc_doc`, `acc_vote`, `macro_f1`, `support`, `per_topic` P/R/F1, `confusion` top-15 pāri, `abstain`) un CLI, kas katrai metodei rēķina tikai uz `split='test'`; Jev un Claude — arī precizitāti/segumu pie sliekšņiem 0.5/0.6/0.7/0.8/0.9 (slieksni izvēlas uz `dev`).
- [ ] **Step 3: Palaid → `ATSKAITE.md`**: tabula metode × (n, acc_doc, acc_vote, macro-F1, segums pie izvēlētā sliekšņa), sajaukšanas pāri, aplēstā cena 2 583 dokumentiem katrai metodei. Saucēji katrā rindā. `test` pusē pēc pašreizējās tēmas nav Droni, Klimats, Sports, Transports (to piemēri ir RUBRIKĀ → `dev`) — atskaitē to pasaka, macro-F1 tās neietver. `acc_vote` uz ķēžu etiķetēm rāda arī bez budžeta ķēdēm (1130/Lp14, 152/Lp14 = 370 no 694), citādi tas mēra budžetus. `NESKAIDRS` rindas — atsevišķa rinda atskaitē. Tēmu skaits kopš 2026-10-22 ir 35. `test` rādītājus dod arī bez 8 rubrikā aprakstītajiem dokumentiem (`AUDITS.md` § Aprakstīti, ne citēti).
- [x] **Step 4: Commit; advisor vārti; STOP** — operatoram vienā rindkopā: uzvarētājs + kāpēc + slieksnis. Ieteikuma noklusējums: augstākais macro-F1 uz `test`; vienādības gadījumā lētākais. **Neturpināt līdz operatora «jā».**
  **Operatora lēmums 2026-10-22:** uzvarētājs Jev, slieksnis 0,9 (`src/saeima/topics.py` `INGEST_CONFIDENCE_THRESHOLD`; CHANGELOG 2026-10-22 (2)).

---

### Task 8: Ielāde lieto lēmumu tabulu

**Files:**
- Modify: `src/saeima/votes.py:510` (`store_vote`)
- Modify: `src/saeima/topics.py` (`topic_for_new_vote`)
- Test: `tests/test_saeima.py` (`TestStoreVoteTopicDecision`)

**Interfaces:**
- Produces: `topic_for_new_vote(db, document_nr, motif, input_text) -> str` — 1) `current_decision(key)` ja ir; 2) citādi uzvarētāja klasifikators → `record_decision(...)` (zem sliekšņa vai `None` → `review_status='pending'`, tēma no `classify_keyword`, `log_action(action='vote_topic_fallback', status='warning')`); 3) `reason='multi'` vai atslēga `None` → atslēgvārdi, `review_status='pending'` + `log_action` (klasifikatoru nesauc).

- [x] **Step 1: Krītošie testi** — (a) dokumentam ar lēmumu jauns balsojums saņem lēmuma tēmu; (b) bez lēmuma un ar `classify_*` → `None` (monkeypatch) → tēma = atslēgvārdi, `saeima_document_topics.review_status='pending'`, `action_log` ir `vote_topic_fallback` rinda; (c) `motif` «Deputātu klātbūtnes reģistrācija» → «Saeimas darbs».
- [x] **Step 2: Implementē; `store_vote` sauc `topic_for_new_vote` `_motif_to_topic` vietā.** Klasifikatora tīkla zvans notiek tikai, ja atslēgai nav lēmuma (viens zvans dokumentam, ne balsojumam).
- [x] **Step 3: Testi + `bash scripts/check.sh` zaļš. Mutācija:** noņem `review_status='pending'` zaru → (b) krīt.
- [x] **Step 4: Atjauno `.claude/agents/saeima-tracker.md` un `/saeima-ingest`** ar vienu rindkopu: kur rodas tēma, ka `pending` dokumenti parādās `scripts/vote_topics.py status`, un ka tos izšķir ar `decide`.
- [x] **Step 5: Commit.** Pirmā dzīvā ielāde pēc tam — pārbaudi `status`, ka jaunie dokumenti saņēma lēmumus. (Kods 2026-10-22; dzīvā ielāde vēl NAV notikusi — pārbaudīts tikai ar `store_vote` DB kopijā.)

---

### Task 9: Partija (atkārto katrā izpildes sesijā)

Partiju saraksts tiek uzģenerēts vienreiz: `scripts/vote_topics.py plan --size 300` (pievieno CLI apakškomandu šajā uzdevumā, ar testu, ka sakārtojums ir deterministisks un pēc ietekmes: vispirms dokumenti ar pašreizējo «Valsts pārvalde», tad «Vide», tad pārējie pēc balsojumu skaita) → `data/saeima_topic_gold/batches.csv` (`batch_id, document_key`), komitēts. ~9 partijas.

- [x] **Operatora lēmums 2026-10-22:** partijām slieksnis 0,7 (`BATCH_CONFIDENCE_THRESHOLD`), ielādei paliek 0,9; Jev piesaistīts `jev-1.14.0` (`JEV_MODEL`, `src/saeima/topics.py`; CHANGELOG 2026-10-22 (4), `ATSKAITE.md` § Jev 1.14 pārmērījums). 4 budžeta likumi partijās nav (`is_budget_law`), līdz operators izlemj (`backlog/saeima.md`).
- [x] **Labojums 2026-10-22:** viens dokuments Jev pieprasījumā (`JEV_CHUNK_SIZE = 1`); partijām slieksnis 0,8, ielādei 0,9 (`ATSKAITE.md` § Jev 1.14, viens dokuments pieprasījumā; CHANGELOG 2026-10-22 (5)). Iepriekšējais 0,7 bija mērīts 16 dokumentu paketēs.

Katrai partijai:

- [ ] **Step 1: Klasificē** dokumentus, kam nav lēmuma, ar uzvarētāju → `record_decision`. Izdrukā: lēmumu skaits, `pending` skaits, cena.
- [ ] **Step 2: Pārbaudes saraksts** — `pending` + visi, kur jaunā tēma ≠ vecā UN pārliecība < 0,9: izlasi pret avotu un izšķir (`decide <key> <topic> --method human`). Izlase: 20 nejauši «auto» lēmumi pret avotu; ja >2 kļūdas → STOP, ziņo. **Mācības no b01 (2026-10-22):** pārbaudītājiem (Opus, katram RUBRIKA.md, katrai rindai burtisks citāts no avota) dod pa ~25 dokumentiem; rindas, kur pārbaudītājs NEpiekrīt Jev ar noteiktību `low`, orķestrētājs pirms `decide` izlasa avotā pats (676/Lp14 aizgāja «Digitālā politika», bet anotācija — direktīva par bērnu garantijām kriminālprocesā → «Tieslietas»). Pēc apply pārbaudi «Saeimas darbs» atslēgas un rubrikā minētos piemērus (267/Lp14 Kārtības rullis — Jev auto 0,90 pret rubriku). Šaubīgos `summary` pieraksti `backlog/saeima.md` un labo ar rollback. **Mācības no b02 (2026-10-22):** ja nejaušajā izlasē > 2 kļūdas, pārbaudi pret avotu VISUS partijas «auto» lēmumus (operatora lēmums; b02: 11/178 kļūdas, 9 no tām ar Jev ≥ 0,9), tāpat pa ~23 dokumentiem pārbaudītājam; atslēgas, kas apvieno nesaistītus balsojumus (`KEY_MIXED`), neiesaldē; pilsonība (arī atņemšana drošības nolūkā) → «Sociālā politika».
- [ ] **Step 3: `freeze <batch_id>`** (atsaka, ja kādam dokumentam lēmums ir `pending` — izšķir 2. solī; `--allow-pending` tikai apzināti; ja rollback faila rakstīšana krīt — `abandon <batch_id>` un freeze no jauna) → izdrukā dalībniekus un snapshot rindu skaitu; rollback fails uzrakstīts.
- [ ] **Step 4: Commit rollback failu** (`git add data/rollback_vote_topics_<batch_id>.sql`, ziņa caur failu).
- [ ] **Step 5: `apply <batch_id>`** — ielāde tajā brīdī NEdrīkst iet: apply tur rakstīšanas slēdzeni ~46 s uz ~313k ierakstu, citu rakstītāju gaidīšanas robeža ir 30 s (sesijas 1 mērījums uz DB kopijas). Ja partija > ~150 lielo dokumentu, sadali. — atskaite: `votes`, `claims` = gaidītie (no 3. soļa), `collisions=0`, `parity_mismatch=0`, pirms/pēc sadalījums. Jebkura novirze → `rollback` un STOP.
- [ ] **Step 6: Pēcpārbaude** — `sync_bill_topics` šīs partijas dokumentiem (10. uzdevuma funkcija; ja vēl nav — izpildi 10. uzdevuma 1.–2. soli pirms pirmās partijas), lai likumu lapas nesāk atšķirties no balsojumu lapām; `party_contradictions` kandidātu skaits pirms/pēc (ieraksti); šaurs renders balsojumu domēnam (`--only=`, sk. `wiki/operations/commands.md`) un viena balsojumu lapa pārlūkā; ja mainās likumu wiki lapas — bāzlīnijas REGEN kā plānots solis.
- [ ] **Step 7: Ieraksts** `data/saeima_topic_gold/BATCH_LOG.md` (datums, partija, skaitļi, rollback fails) + commit. Deploy — tikai ar operatora atļauju.

---

### Task 10: Noslēgums

**Files:**
- Modify: `src/saeima/topics.py` (`sync_bill_topics(db)`), `src/render/laws.py` nemainās (lasa `saeima_bills.topic`)
- Modify: `CLAUDE.md` («33 canonical groups» → 34), `wiki/CHANGELOG.md`, `backlog/saeima.md` (ieraksts → `[SLĒGTS]` vai atlikums), `src/saeima/claims.py` komentārs ar mirušo `backlog/saeima.md § _motif_to_topic()` atsauci → uz spec
- Test: `tests/test_saeima_topics.py::test_sync_bill_topics_from_decisions`

- [ ] **Step 1: Krītošais tests** — `saeima_bills` rinda ar `document_nr='412/Lp14'`, `topic=NULL`; lēmums «Tieslietas» → `sync_bill_topics` → `topic='Tieslietas'`.
- [ ] **Step 2: Implementē** (ar snapshot + rollback kā partijai, jo raksta esošas rindas; rollback fails komitēts pirms dzīvās palaišanas).
- [ ] **Step 3: Dokumentācija** — CHANGELOG ≤5 rindas (kas, skaitļi ar vaicājumu, rollback faili); CLAUDE.md 34; gramatikas vārti.
- [ ] **Step 4: `bash scripts/check.sh`** zaļš; commit; advisor; ziņojums operatoram.
