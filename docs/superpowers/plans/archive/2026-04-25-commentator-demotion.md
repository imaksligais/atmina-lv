# Commentator demotion + profile X subtab — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Likvidēt commentator-as-politician antishablonu — 7 komentētājus (Heinrih5, Kurmitis_, Klucis, Tuksumsz, Svirskis, Lūsis, PStrautins) demote no `tracked_politicians` uz `social_accounts.feed_type='relay'`, lai viņu tvīti turpina ielādēties bet iet caur tekstu skenējošo matcher; pievienot politiķa profila lapai jaunu X subtabu, kas rāda twitter + x_mention dokumentus, kuros politiķis ir subject vai mentioned.

**Architecture:** 3 koordinētas izmaiņas vienā plānā. (1) DB migrācija — pārveido 7 commentator rindas: noņemt no `tracked_politicians`, pārliekt to `social_accounts` rindas no `feed_type='first_party'` uz `'relay'`, izveidot trūkstošās. (2) Esošo dokumentu re-link — `link_politicians_to_documents(rescan_all=True)` pēc pārejošo subject-tipa linkķu noņemšanas, lai matcher tekstā atrod mentioned politiķus. (3) Profila X subtaba — jauna 8. subtaba, fetcher ar `platform IN ('twitter','x_mention')` + `role IN ('subject','mentioned','mention_target')` filtru, render template ar mention-card paraugu. Esošās commentary claims (vēsturiskās, pirms 2026-04-25) paliek DB un Komentāri subtabā kā audit trail; jaunas vairs nerodas.

**Tech Stack:** SQLite (WAL) + idempotentas migrācijas `init_db` blokā · Python 3.11 · pytest · Jinja2 templates · esoši `_store_tweets` (relay path) un `link_politicians_to_documents(rescan_all=True)` mehānismi.

---

## Failu struktūra

**Modificējami:**
- `src/generate.py:1326-1470` — `_fetch_politician_detail` paplašināt ar `x_posts` query (twitter + x_mention dokumenti)
- `templates/politician.html.j2:52-90` — pievienot X subtabas pogu profile-stats-bar; pievienot `tab-x` div pirms `tab-zinas` ap rindu 372
- `tests/test_generate.py` — `_fetch_politician_detail` x_posts atgriešanas tests
- `wiki/CHANGELOG.md` — pievienot 2026-04-25 commentator demotion ierakstu
- `CLAUDE.md` — §12 atjaunināt: commentator nav vairs valid relationship_type tracked_politicians; demotēti uz relay social_accounts

**Jauni:**
- `scripts/migrate_commentator_demotion.py` — vienreizējs idempotents skripts. Pārveido 7 commentators: noņemt `tracked_politicians.relationship_type` uz `'inactive'` (lai dokumenti ar speaker_id paliek validi), pārveidot to `social_accounts.feed_type` uz `'relay'`, izveidot trūkstošās relay rindas. Drīkst palaist atkārtoti.
- `scripts/relink_commentator_documents.py` — vienreizējs skripts. Atrod visus dokumentus, kur `subject` role piesaistīts demotētam commentator (pid IN demotion list), izdzēš tos role='subject' linkus, palaiž `link_politicians_to_documents(rescan_all=True)` lai re-skenē tekstā mentioned politiķus.
- `tests/test_migrate_commentator_demotion.py` — migrācijas idempotences tests
- `tests/test_relink_commentator_documents.py` — re-link integrity tests

---

## Sākotnējais konteksts (pirms uzsākšanas)

Šajā sesijā jau veikta tīrīšana: `scripts/cleanup_2026_04_25_commentator_data.py` izpildījies 2026-04-25 — 8 šodienas commentary claims (claim_type='commentary' AND date(created_at)='2026-04-25') un 8 tensions (id 75-82) izdzēstas, vietne pārģenerēta. Backup: `data/backups/cleanup_2026-04-25_commentator-prep.json`. Šis plāns sākas no šī tīrā stāvokļa.

7 demotējamie commentators (verificēti 2026-04-25):

| pid | name | x_handle |
|---|---|---|
| 62 | Edgars Svirskis | @ESvirskis (+@realNepareizais) |
| 169 | Didzis Kļuciņš | @KlucisD |
| 171 | @Heinrih5 | @Heinrih5 |
| 172 | @Tuksumsz | @Tuksumsz |
| 174 | Toms Lūsis | @LusisToms |
| 175 | @Kurmitis_ | @Kurmitis_ |
| 177 | @PStrautins | @PStrautins |

Vēsturiskās commentary claims (pirms 2026-04-25), kas saglabājas:

```sql
SELECT COUNT(*), speaker_id FROM claims
WHERE claim_type='commentary' AND date(created_at) < '2026-04-25'
GROUP BY speaker_id;
```

Šīs paliek DB neskartas. Nedzēš. Komentāri subtaba turpina rādīt vēsturisko, līdz 90-d. logs natural paiet.

---

## Task 1: Audit skripts — verificēt pašreizējo stāvokli

**Files:**
- Create: `scripts/audit_commentator_state.py`

- [ ] **Step 1: Uzrakstīt audit skriptu**

Izveido `scripts/audit_commentator_state.py`:

```python
"""Pre-migration audit: print current state of 7 commentators.
Run: python scripts/audit_commentator_state.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("data/atmina.db")
COMMENTATOR_IDS = [62, 169, 171, 172, 174, 175, 177]


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    print("=== tracked_politicians ===")
    rows = con.execute(
        f"SELECT id, name, party, x_handle, relationship_type "
        f"FROM tracked_politicians WHERE id IN ({','.join('?' * 7)})",
        COMMENTATOR_IDS,
    ).fetchall()
    for r in rows:
        print(f"  pid={r['id']:4} {r['name']:30} rel={r['relationship_type']} handle=@{r['x_handle']}")

    print("\n=== social_accounts ===")
    rows = con.execute(
        f"SELECT opponent_id, platform, handle, feed_type, active "
        f"FROM social_accounts WHERE opponent_id IN ({','.join('?' * 7)})",
        COMMENTATOR_IDS,
    ).fetchall()
    for r in rows:
        print(f"  pid={r['opponent_id']:4} {r['platform']:8} @{r['handle']:20} feed={r['feed_type']} active={r['active']}")

    print("\n=== documents w/ commentator as subject (last 30 days) ===")
    cutoff = "datetime('now','-30 day')"
    rows = con.execute(
        f"SELECT dp.politician_id, COUNT(*) as cnt "
        f"FROM document_politicians dp "
        f"JOIN documents d ON d.id = dp.document_id "
        f"WHERE dp.politician_id IN ({','.join('?' * 7)}) AND dp.role='subject' "
        f"AND d.scraped_at >= {cutoff} "
        f"GROUP BY dp.politician_id",
        COMMENTATOR_IDS,
    ).fetchall()
    for r in rows:
        print(f"  pid={r['politician_id']:4}: {r['cnt']} docs as subject")

    print("\n=== claims w/ speaker_id IN commentators (historical) ===")
    rows = con.execute(
        f"SELECT speaker_id, COUNT(*) as cnt FROM claims "
        f"WHERE speaker_id IN ({','.join('?' * 7)}) GROUP BY speaker_id",
        COMMENTATOR_IDS,
    ).fetchall()
    for r in rows:
        print(f"  speaker_id={r['speaker_id']}: {r['cnt']} historical commentary claims")

    print("\n=== tensions w/ source_pid OR target_pid IN commentators ===")
    rows = con.execute(
        f"SELECT source_pid, target_pid, COUNT(*) as cnt FROM political_tensions "
        f"WHERE source_pid IN ({','.join('?' * 7)}) OR target_pid IN ({','.join('?' * 7)}) "
        f"GROUP BY source_pid, target_pid",
        COMMENTATOR_IDS + COMMENTATOR_IDS,
    ).fetchall()
    for r in rows:
        print(f"  {r['source_pid']}->{r['target_pid']}: {r['cnt']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Palaist audit un saglabāt baseline**

Run:
```bash
PYTHONPATH=. python scripts/audit_commentator_state.py | tee data/backups/audit_pre_demotion_2026-04-25.txt
```

Expected output (sample): pid=171 Heinrih5 ar `relationship_type=commentator`, `social_accounts` rindu var nebūt vai var būt ar `feed_type='first_party'`, ~5-15 docs/30d kā subject, vēsturiskās commentary claims un attiecīgās tensions.

- [ ] **Step 3: Commit**

```bash
git add scripts/audit_commentator_state.py data/backups/audit_pre_demotion_2026-04-25.txt
git commit -m "chore(audit): commentator pre-demotion state snapshot"
```

---

## Task 2: Migrācijas skripts — demotēt 7 commentators

**Files:**
- Create: `scripts/migrate_commentator_demotion.py`
- Test: `tests/test_migrate_commentator_demotion.py`

- [ ] **Step 1: Uzrakstīt failējošu testu**

Izveido `tests/test_migrate_commentator_demotion.py`:

```python
"""Tests for scripts/migrate_commentator_demotion.py — idempotency, completeness."""
import sqlite3
from pathlib import Path

import pytest

from scripts.migrate_commentator_demotion import COMMENTATOR_IDS, demote_commentators


@pytest.fixture
def temp_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    con = sqlite3.connect(db_path)
    con.executescript("""
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY,
            name TEXT, party TEXT, x_handle TEXT,
            relationship_type TEXT
        );
        CREATE TABLE social_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opponent_id INTEGER,
            platform TEXT, handle TEXT,
            feed_type TEXT DEFAULT 'first_party',
            active BOOLEAN DEFAULT 1
        );
    """)
    # Seed minimal commentator state
    con.execute(
        "INSERT INTO tracked_politicians (id, name, x_handle, relationship_type) VALUES "
        "(171, '@Heinrih5', 'Heinrih5', 'commentator'), "
        "(175, '@Kurmitis_', 'Kurmitis_', 'commentator')"
    )
    con.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type, active) VALUES "
        "(171, 'twitter', 'Heinrih5', 'first_party', 1)"
        # 175 has no social_accounts row — migration must create it
    )
    con.commit()
    return con


def test_demotion_changes_relationship_type_to_inactive(temp_db: sqlite3.Connection):
    demote_commentators(temp_db, only_ids=[171, 175])
    row = temp_db.execute("SELECT relationship_type FROM tracked_politicians WHERE id=171").fetchone()
    assert row[0] == "inactive"


def test_demotion_sets_feed_type_relay_for_existing_social_account(temp_db: sqlite3.Connection):
    demote_commentators(temp_db, only_ids=[171, 175])
    row = temp_db.execute(
        "SELECT feed_type FROM social_accounts WHERE opponent_id=171 AND platform='twitter'"
    ).fetchone()
    assert row[0] == "relay"


def test_demotion_creates_missing_social_account(temp_db: sqlite3.Connection):
    demote_commentators(temp_db, only_ids=[171, 175])
    row = temp_db.execute(
        "SELECT handle, feed_type, active FROM social_accounts "
        "WHERE opponent_id=175 AND platform='twitter'"
    ).fetchone()
    assert row is not None
    assert row[0] == "Kurmitis_"
    assert row[1] == "relay"
    assert row[2] == 1


def test_demotion_is_idempotent(temp_db: sqlite3.Connection):
    demote_commentators(temp_db, only_ids=[171, 175])
    demote_commentators(temp_db, only_ids=[171, 175])  # second call
    sa_count = temp_db.execute(
        "SELECT COUNT(*) FROM social_accounts WHERE opponent_id IN (171, 175) AND platform='twitter'"
    ).fetchone()[0]
    assert sa_count == 2  # not 3+ — second call must not duplicate


def test_demotion_preserves_unrelated_politicians(temp_db: sqlite3.Connection):
    temp_db.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Politiķis', 'tracked')"
    )
    temp_db.commit()
    demote_commentators(temp_db, only_ids=[171, 175])
    row = temp_db.execute("SELECT relationship_type FROM tracked_politicians WHERE id=1").fetchone()
    assert row[0] == "tracked"
```

- [ ] **Step 2: Palaist testus — verificēt fail**

Run: `pytest tests/test_migrate_commentator_demotion.py -v`
Expected: ImportError (skripta nav).

- [ ] **Step 3: Uzrakstīt migrācijas skriptu**

Izveido `scripts/migrate_commentator_demotion.py`:

```python
"""Demote 7 commentators from tracked_politicians to social_accounts relay-only.

Idempotent — drīkst palaist atkārtoti. Veic 3 darbības per commentator:
1. tracked_politicians.relationship_type: 'commentator' -> 'inactive'
   (Saglabā rindu, lai vēsturiskās commentary claims ar speaker_id FK
   paliek validas. 'inactive' filtrē no profila ģenerēšanas un
   get_pending_politicians.)
2. social_accounts: ja rinda eksistē — feed_type -> 'relay'.
   Ja ne — INSERT (opponent_id, platform='twitter', handle, feed_type='relay').
3. Nesaska ar tracked_politicians.x_handle (paliek; tas ir audit trail).
"""
import argparse
import sqlite3
from pathlib import Path


COMMENTATOR_IDS = [62, 169, 171, 172, 174, 175, 177]


def demote_commentators(con: sqlite3.Connection, only_ids: list[int] | None = None) -> dict:
    """Run demotion. Returns counts dict."""
    ids = only_ids if only_ids is not None else COMMENTATOR_IDS
    placeholders = ",".join("?" * len(ids))

    counts = {"reltype_updated": 0, "social_updated": 0, "social_created": 0}

    cur = con.cursor()

    cur.execute(
        f"UPDATE tracked_politicians SET relationship_type='inactive' "
        f"WHERE id IN ({placeholders}) AND relationship_type='commentator'",
        ids,
    )
    counts["reltype_updated"] = cur.rowcount

    for pid in ids:
        handle_row = con.execute(
            "SELECT x_handle FROM tracked_politicians WHERE id=?", (pid,)
        ).fetchone()
        if not handle_row or not handle_row[0]:
            continue
        handle = handle_row[0].lstrip("@")

        existing = con.execute(
            "SELECT id, feed_type FROM social_accounts "
            "WHERE opponent_id=? AND platform='twitter'",
            (pid,),
        ).fetchone()
        if existing:
            if existing[1] != "relay":
                cur.execute(
                    "UPDATE social_accounts SET feed_type='relay' WHERE id=?",
                    (existing[0],),
                )
                counts["social_updated"] += 1
        else:
            cur.execute(
                "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type, active) "
                "VALUES (?, 'twitter', ?, 'relay', 1)",
                (pid, handle),
            )
            counts["social_created"] += 1

    con.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/atmina.db")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    if args.dry_run:
        print(f"DRY RUN — no commits. Demoting {len(COMMENTATOR_IDS)} commentators...")
        # In dry-run, run inside a transaction and rollback
        try:
            counts = demote_commentators(con)
            con.rollback()
            print(f"Would update: relationship_type={counts['reltype_updated']}, "
                  f"social_accounts updated={counts['social_updated']}, "
                  f"created={counts['social_created']}")
        finally:
            con.close()
        return

    counts = demote_commentators(con)
    print(f"Demoted: relationship_type updated={counts['reltype_updated']}, "
          f"social_accounts updated={counts['social_updated']}, "
          f"created={counts['social_created']}")
    con.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Palaist testus — verificēt pass**

Run: `pytest tests/test_migrate_commentator_demotion.py -v`
Expected: 5 passed.

- [ ] **Step 5: Dry-run pret reālo DB**

Run:
```bash
PYTHONPATH=. python scripts/migrate_commentator_demotion.py --dry-run
```
Expected output:
```
DRY RUN — no commits. Demoting 7 commentators...
Would update: relationship_type=7, social_accounts updated=N, created=M
```
(N+M = 7 — visi septiņi tiek atspoguļoti vai nu update, vai create.)

- [ ] **Step 6: Reāla migrācija**

Run:
```bash
PYTHONPATH=. python scripts/migrate_commentator_demotion.py
```
Expected: same counts but no DRY RUN prefix.

- [ ] **Step 7: Verificēt ar audit skriptu**

Run: `PYTHONPATH=. python scripts/audit_commentator_state.py`
Expected: visi 7 commentators tagad ar `relationship_type=inactive`, social_accounts ar `feed_type=relay`.

- [ ] **Step 8: Commit**

```bash
git add scripts/migrate_commentator_demotion.py tests/test_migrate_commentator_demotion.py
git commit -m "feat(migrate): demote 7 commentators to social_accounts relay"
```

---

## Task 3: Re-link existing commentator-authored documents

**Files:**
- Create: `scripts/relink_commentator_documents.py`
- Test: `tests/test_relink_commentator_documents.py`

- [ ] **Step 1: Uzrakstīt failējošu testu**

Izveido `tests/test_relink_commentator_documents.py`:

```python
"""Tests for scripts/relink_commentator_documents.py — verify subject links removed
and link_politicians_to_documents re-scans for mentioned politicians."""
import sqlite3
from pathlib import Path

import pytest

from scripts.relink_commentator_documents import remove_subject_links_for_demoted


@pytest.fixture
def temp_db(tmp_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(tmp_path / "test.db")
    con.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY, content TEXT, source_url TEXT,
            platform TEXT, scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE document_politicians (
            document_id INTEGER, politician_id INTEGER, role TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Seed: 3 docs authored by demoted commentator (171, role='subject');
    # one of them also mentions politician 157 as 'mentioned' from prior matcher run
    con.executescript("""
        INSERT INTO documents (id, content, source_url, platform) VALUES
            (101, 'Lūgums @ltvzinas par Melni', 'https://x.com/Heinrih5/status/1', 'twitter'),
            (102, 'Cits tvīts', 'https://x.com/Heinrih5/status/2', 'twitter'),
            (103, 'Vēl viens', 'https://x.com/Heinrih5/status/3', 'twitter');
        INSERT INTO document_politicians (document_id, politician_id, role) VALUES
            (101, 171, 'subject'),
            (101, 157, 'mentioned'),
            (102, 171, 'subject'),
            (103, 171, 'subject');
    """)
    con.commit()
    return con


def test_removes_subject_links_for_demoted_pids(temp_db: sqlite3.Connection):
    removed = remove_subject_links_for_demoted(temp_db, demoted_pids=[171])
    assert removed == 3
    rows = temp_db.execute(
        "SELECT COUNT(*) FROM document_politicians WHERE politician_id=171 AND role='subject'"
    ).fetchone()
    assert rows[0] == 0


def test_preserves_other_role_links_for_demoted(temp_db: sqlite3.Connection):
    """If demoted commentator was tagged 'mentioned' on some doc, that link survives —
    only role='subject' is the structural lie we want to undo."""
    temp_db.execute(
        "INSERT INTO document_politicians (document_id, politician_id, role) VALUES (101, 171, 'mentioned')"
    )
    temp_db.commit()
    remove_subject_links_for_demoted(temp_db, demoted_pids=[171])
    rows = temp_db.execute(
        "SELECT COUNT(*) FROM document_politicians WHERE politician_id=171 AND role='mentioned'"
    ).fetchone()
    assert rows[0] == 1


def test_preserves_other_politicians_subject_links(temp_db: sqlite3.Connection):
    """Mentioned politician (157) on doc 101 must remain after demotion."""
    remove_subject_links_for_demoted(temp_db, demoted_pids=[171])
    rows = temp_db.execute(
        "SELECT COUNT(*) FROM document_politicians WHERE politician_id=157 AND role='mentioned'"
    ).fetchone()
    assert rows[0] == 1


def test_idempotent(temp_db: sqlite3.Connection):
    remove_subject_links_for_demoted(temp_db, demoted_pids=[171])
    removed_again = remove_subject_links_for_demoted(temp_db, demoted_pids=[171])
    assert removed_again == 0
```

- [ ] **Step 2: Palaist testus — verificēt fail**

Run: `pytest tests/test_relink_commentator_documents.py -v`
Expected: ImportError.

- [ ] **Step 3: Uzrakstīt skriptu**

Izveido `scripts/relink_commentator_documents.py`:

```python
"""Re-link commentator-authored documents after demotion.

Strategy:
1. DELETE document_politicians rows where role='subject' AND politician_id IN demoted_pids.
   These were inserted by `_store_tweets` first_party path; after demotion these
   handles go through relay path which leaves politician_links empty.
2. Run link_politicians_to_documents(rescan_all=True). It will pick up the now
   unlinked docs (no document_politicians row at all) and text-scan for any
   tracked politician mentions, attaching role='mentioned' or 'mention_target'
   as appropriate.

Result: a Heinrih5 tweet that mentions "Melni" in its body now links Melnis
(157) as 'mentioned' and is visible on Melnis's profile X subtab.
"""
import argparse
import sqlite3
from pathlib import Path

DEMOTED_PIDS = [62, 169, 171, 172, 174, 175, 177]


def remove_subject_links_for_demoted(
    con: sqlite3.Connection, demoted_pids: list[int]
) -> int:
    """DELETE document_politicians rows where role='subject' AND politician_id IN demoted.
    Returns count of rows deleted."""
    placeholders = ",".join("?" * len(demoted_pids))
    cur = con.cursor()
    cur.execute(
        f"DELETE FROM document_politicians "
        f"WHERE role='subject' AND politician_id IN ({placeholders})",
        demoted_pids,
    )
    con.commit()
    return cur.rowcount


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/atmina.db")
    parser.add_argument("--days", type=int, default=30,
                        help="Window for link_politicians_to_documents rescan")
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    removed = remove_subject_links_for_demoted(con, DEMOTED_PIDS)
    print(f"Removed {removed} role='subject' links for {len(DEMOTED_PIDS)} demoted commentators")
    con.close()

    # Now invoke text-scanning matcher on rescan_all. Pass days large enough to
    # cover the recently unlinked tweets — in practice these were scraped in the
    # last weeks, so 30 days is a safe default.
    from src.ingest import link_politicians_to_documents
    linked = link_politicians_to_documents(days=args.days, rescan_all=True)
    total_links = sum(len(v) for v in linked.values())
    print(f"link_politicians_to_documents: {len(linked)} docs got new links, "
          f"{total_links} total politician-doc links added")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Palaist testus — verificēt pass**

Run: `pytest tests/test_relink_commentator_documents.py -v`
Expected: 4 passed.

- [ ] **Step 5: Reāla re-link palaišana**

Run:
```bash
PYTHONPATH=. python scripts/relink_commentator_documents.py --days 30
```
Expected output:
```
Removed N role='subject' links for 7 demoted commentators
link_politicians_to_documents: M docs got new links, K total politician-doc links added
```
(N ~ 50-200 atkarībā no tvītu vēstures; M ~ 30-80; K ~ M līdz 2*M.)

- [ ] **Step 6: Verificēt sample case — Heinrih5 doc 25608**

Run:
```bash
sqlite3 data/atmina.db "SELECT politician_id, role FROM document_politicians WHERE document_id=25608"
```
Expected: vismaz viena rinda ar `politician_id=157, role='mentioned'` (Melnis tika atrasts tekstā). Var būt arī citu politiķu rindas. NEDRĪKST būt rinda ar `politician_id=171, role='subject'` (jau dzēsta).

- [ ] **Step 7: Commit**

```bash
git add scripts/relink_commentator_documents.py tests/test_relink_commentator_documents.py
git commit -m "feat(migrate): re-link demoted commentator documents via text-scan"
```

---

## Task 4: Pievienot X subtabas datu fetcher `_fetch_politician_detail`

**Files:**
- Modify: `src/generate.py:1326-1470` (zonā, kur tiek apkopots `_fetch_politician_detail` rezultāts)
- Test: `tests/test_generate.py`

- [ ] **Step 1: Uzrakstīt failējošu testu**

Pievieno `tests/test_generate.py`:

```python
def test_fetch_politician_detail_returns_x_posts(tmp_path):
    """X subtab data: documents WHERE platform IN ('twitter','x_mention')
    AND linked to politician via document_politicians, ordered by published_at DESC."""
    import sqlite3
    from src.generate import _fetch_politician_detail

    db_path = tmp_path / "test.db"
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    # Minimal schema for this test (real init_db is too broad)
    con.executescript("""
        CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, party TEXT);
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY, content TEXT, source_url TEXT,
            source_domain TEXT, platform TEXT, published_at TIMESTAMP,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, language TEXT
        );
        CREATE TABLE document_politicians (
            document_id INTEGER, politician_id INTEGER, role TEXT
        );
        CREATE TABLE claims (id INTEGER PRIMARY KEY);  -- empty
        CREATE TABLE contradictions (id INTEGER PRIMARY KEY);  -- empty
        CREATE TABLE political_tensions (id INTEGER PRIMARY KEY);  -- empty
        CREATE TABLE saeima_votes (id INTEGER PRIMARY KEY);  -- empty
        CREATE TABLE external_profiles (
            id INTEGER PRIMARY KEY, opponent_id INTEGER, platform TEXT,
            url TEXT, handle TEXT, display_label TEXT, active INT DEFAULT 1
        );
    """)
    con.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (157, 'Kaspars Melnis', 'ZZS')")
    con.execute("""
        INSERT INTO documents (id, content, source_url, source_domain, platform, published_at, language)
        VALUES
            (1, 'Tweet body about Melni', 'https://x.com/Heinrih5/status/1', 'x.com', 'twitter', '2026-04-25', 'lv'),
            (2, 'Mention reply', 'https://x.com/User/status/2', 'x.com', 'x_mention', '2026-04-24', 'lv'),
            (3, 'Web article', 'https://lsm.lv/...', 'lsm.lv', 'web', '2026-04-23', 'lv')
    """)
    con.execute("""
        INSERT INTO document_politicians (document_id, politician_id, role) VALUES
            (1, 157, 'mentioned'),
            (2, 157, 'mention_target'),
            (3, 157, 'subject')
    """)
    con.commit()

    # Monkey-patch get_db to use our temp DB
    import src.generate
    original_get_db = src.generate.get_db
    src.generate.get_db = lambda: con
    try:
        result = _fetch_politician_detail(157)
    finally:
        src.generate.get_db = original_get_db

    assert "x_posts" in result, "x_posts key missing from _fetch_politician_detail"
    assert len(result["x_posts"]) == 2, "should return 2 X posts (twitter + x_mention)"
    # Order: published_at DESC
    assert result["x_posts"][0]["id"] == 1
    assert result["x_posts"][1]["id"] == 2
    # Web doc is filtered out (it goes to news, not x_posts)
    ids = [p["id"] for p in result["x_posts"]]
    assert 3 not in ids
```

- [ ] **Step 2: Palaist testu — fail**

Run: `pytest tests/test_generate.py::test_fetch_politician_detail_returns_x_posts -v`
Expected: FAIL ar "x_posts key missing".

- [ ] **Step 3: Modificēt `_fetch_politician_detail`**

Atver `src/generate.py`. Pirms `return {` rindas (~1458) pievieno:

```python
    x_posts_rows = db.execute("""
        SELECT d.id, d.content, d.source_url, d.source_domain,
               d.platform, d.published_at, d.scraped_at, d.language,
               dp.role
        FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        WHERE dp.politician_id = ?
          AND d.platform IN ('twitter', 'x_mention')
        ORDER BY COALESCE(d.published_at, d.scraped_at) DESC
        LIMIT 50
    """, (pid,)).fetchall()
    x_posts = [dict(r) for r in x_posts_rows]
```

Tad pievieno `"x_posts": x_posts,` rezultāta dict (alfabētiski starp `votes` un kādu citu).

- [ ] **Step 4: Palaist testu — pass**

Run: `pytest tests/test_generate.py::test_fetch_politician_detail_returns_x_posts -v`
Expected: PASS.

- [ ] **Step 5: Palaist visus generate testus**

Run: `pytest tests/test_generate.py -v`
Expected: all pass — pārliecināties, ka esoši testi nav salauzti.

- [ ] **Step 6: Commit**

```bash
git add src/generate.py tests/test_generate.py
git commit -m "feat(generate): add x_posts fetcher to _fetch_politician_detail"
```

---

## Task 5: Pievienot X subtabu politiķa profila template

**Files:**
- Modify: `templates/politician.html.j2:52-90` (profile-stats-bar)
- Modify: `templates/politician.html.j2:370-385` (tab area)

- [ ] **Step 1: Pievienot X subtabas pogu profile-stats-bar**

Atver `templates/politician.html.j2`. Atrod blokā ap rindām 86-89:

```jinja
      {% if news %}
      <button class="profile-stat" onclick="showProfileTab('zinas', this)" data-tab="zinas">
        <span class="profile-stat-value">{{ news|length }}</span>
        <span class="profile-stat-label">Ziņas</span>
      </button>
      {% endif %}
```

Pievieno PIRMS šī bloka:

```jinja
      {% if x_posts %}
      <button class="profile-stat" onclick="showProfileTab('x', this)" data-tab="x">
        <span class="profile-stat-value">{{ x_posts|length }}</span>
        <span class="profile-stat-label">X</span>
      </button>
      {% endif %}
```

- [ ] **Step 2: Pievienot X tab div**

Atrod `<!-- Ziņas tab -->` (~rinda 370). PIRMS šī komentāra pievieno:

```jinja
  <!-- X tab -->
  {% if x_posts %}
  <div class="profile-tab" id="tab-x" style="display:none;">
    {% for p in x_posts %}
    <div class="card" style="margin-bottom:0.75rem;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
        <span style="color:var(--text-muted); font-size:0.8rem;">
          {{ p.source_domain or 'x.com' }}
          {% if p.role == 'mentioned' %}
            <span style="background:var(--bg-muted,#f0f0f0); padding:0.1rem 0.4rem; border-radius:3px; font-size:0.7rem;">pieminēts</span>
          {% elif p.role == 'mention_target' %}
            <span style="background:var(--bg-muted,#f0f0f0); padding:0.1rem 0.4rem; border-radius:3px; font-size:0.7rem;">pieminējums</span>
          {% endif %}
          {% if p.platform == 'x_mention' %}
            <span style="font-size:0.7rem; opacity:0.7;">· mention</span>
          {% endif %}
        </span>
        <span style="color:var(--text-muted); font-size:0.8rem;">
          {{ (p.published_at or p.scraped_at)[:10] if (p.published_at or p.scraped_at) else '' }}
        </span>
      </div>
      <div style="font-size:0.9rem; white-space:pre-wrap;">{{ p.content[:280] }}{% if p.content and p.content|length > 280 %}…{% endif %}</div>
      {% if p.source_url %}<a href="{{ p.source_url | safe_url }}" target="_blank" rel="noopener" style="font-size:0.8rem;">Atvērt X ↗</a>{% endif %}
    </div>
    {% endfor %}
  </div>
  {% endif %}
```

- [ ] **Step 3: Pārbaudīt JS tab switching**

`showProfileTab` funkcija (rinda ~390) jau apstrādā jebkuru `tab-XXX` ID, tāpēc papildu JS izmaiņas nav vajadzīgas.

- [ ] **Step 4: Pārģenerēt vietni un atvērt vienu profilu**

Run:
```bash
PYTHONPATH=. python -c "from src.generate import generate_public_site; generate_public_site()"
```
Expected: nav errors, atklāj `output/atmina/politiki/kaspars-melnis.html` un manuāli pārbaudi:
- Profile stats bar rāda jaunu pogu "X"
- Klikšķinot uz "X" parādās tabs ar Heinrih5 tvītu, kas piemin Melni
- Klikšķinot atpakaļ uz "Pozīcijas" — viss strādā kā agrāk

- [ ] **Step 5: Manuālā UI testēšana**

Atver browser-ā `output/atmina/politiki/kaspars-melnis.html`. Klikšķini visus subtabu — laika līnija, pozīcijas, pretrunas, komentāri, balsojumi, spriedzes, X, ziņas. Visi pārslēdzas pareizi. X tabs rāda mentions — sagaidi vismaz Heinrih5 tvītu un, iespējams, citu commentator pieminējumus.

- [ ] **Step 6: Commit**

```bash
git add templates/politician.html.j2
git commit -m "feat(profile): add X subtab showing twitter + x_mention docs"
```

---

## Task 6: Komentāri subtaba "tukšā stāvokļa" apstrāde

**Files:**
- Modify: `templates/politician.html.j2:189-228`

Mērķis: pēc demotēšanas vēsturiskās commentary claims (pirms 2026-04-25) joprojām eksistē, bet tās ir lietas, kas nāca no commentator pipeline. Komentāri subtaba poga jau ir conditional uz `commentary_about|length`. Ja politiķim nav vēsturisku commentary claims — poga vispār neparādās (jau pareiza uzvedība). Ja ir — parādās ar count un tabs ar saturu.

Bet lasītājs varētu apjukt: kāpēc dažiem politiķiem ir Komentāri subtab, citiem nav? Pievienosim mazu paskaidrojumu zem virsraksta.

- [ ] **Step 1: Modificēt komentāri subtabas intro tekstu**

Atrod rindas 192-198:

```jinja
      <h2 id="komentari-heading">Trešo pušu komentāri par {{ politician.name }} ({{ commentary_about|length }})</h2>
      <p class="komentari-intro">
        Publiskas trešo pušu izteiksmes par {{ politician.name }} — komentētāju, žurnālistu
        un sabiedrisko vērotāju apgalvojumi. <strong>Šie nav {{ politician.name }}
        pozīcijas</strong>, bet gan citu cilvēku publiski pieejami apgalvojumi par
        {{ politician.name }}. Katrs ieraksts ir ņemts no konkrēta avota ar datumu.
      </p>
```

Aizvieto ar:

```jinja
      <h2 id="komentari-heading">Trešo pušu komentāri par {{ politician.name }} ({{ commentary_about|length }})</h2>
      <p class="komentari-intro">
        Publiskas trešo pušu izteiksmes par {{ politician.name }} — komentētāju, žurnālistu
        un sabiedrisko vērotāju apgalvojumi. <strong>Šie nav {{ politician.name }}
        pozīcijas</strong>, bet gan citu cilvēku publiski pieejami apgalvojumi par
        {{ politician.name }}. Katrs ieraksts ir ņemts no konkrēta avota ar datumu.
      </p>
      <p class="komentari-intro" style="font-size:0.85rem; color:var(--text-muted);">
        <em>Vēsturiski (pirms 2026-04-25) komentāri tika kurēti no atsevišķi sekotiem komentētāju
        kontiem. Pašlaik šī sadaļa rāda tikai vēsturisko datu. Aktuālos pieminējumus skaties X
        subtabā.</em>
      </p>
```

- [ ] **Step 2: Pārģenerēt vietni un pārbaudīt politiķi ar vēsturiskām commentary**

Run:
```bash
PYTHONPATH=. python -c "from src.generate import generate_public_site; generate_public_site()"
```
Atver browser-ā politiķi, kuram bija commentary pirms 2026-04-25 (piem., kāds, ko bieži pieminēja Klucis vai Heinrih5 — pieņemam Sprūds vai Siliņa). Verificē intro paskaidrojuma rindu zem virsraksta.

- [ ] **Step 3: Commit**

```bash
git add templates/politician.html.j2
git commit -m "docs(profile): clarify Komentāri subtab is historical post-demotion"
```

---

## Task 7: CLAUDE.md + CHANGELOG atjaunināšana

**Files:**
- Modify: `CLAUDE.md` (§12 invariants)
- Modify: `wiki/CHANGELOG.md` (pievienot 2026-04-25 ierakstu)

- [ ] **Step 1: Atjaunot CLAUDE.md §12**

Atrod CLAUDE.md §12 invariantu (`Social feed_type`). Pievieno blakus esošajiem norādījumiem:

```
**Note (2026-04-25):** `relationship_type='commentator'` vairs nav valid jaunām
rindām — 7 vēsturiskie commentators (Heinrih5, Kurmitis_, Klucis, Tuksumsz,
Svirskis, Lūsis, PStrautins) demotēti uz `'inactive'` + `social_accounts.feed_type='relay'`.
Viņu tvīti turpina ielādēties caur relay path, mentioned politiķi tiek atrasti
ar `link_politicians_to_documents` text scan. Vēsturiskās commentary claims
(pre-2026-04-25) paliek DB ar `speaker_id` FK.
```

- [ ] **Step 2: Pievienot CHANGELOG ierakstu**

Pievieno `wiki/CHANGELOG.md` augšpusē (jaunākais virsū):

```markdown
## 2026-04-25 — commentator demotion: tracked_politicians → social_accounts relay

Demotēti 7 commentators no `tracked_politicians.relationship_type='commentator'`
uz `'inactive'` + `social_accounts.feed_type='relay'`. Iemesls: commentator-as-politician
modelis bija ghosting profilus (commentators bija tracked_politicians, bet to lapas netika
ģenerētas) un radīja konceptuālu sajaukšanos starp first-party pozīcijām un trešo pušu
komentāriem. Pēc demotēšanas viņu tvīti turpina ielādēties caur relay path
(`_store_tweets` ar `feed_type='relay'`), un `link_politicians_to_documents` tekstu
skenē, lai atrastu mentioned tracked politicians.

**Migration:** `scripts/migrate_commentator_demotion.py` + `scripts/relink_commentator_documents.py`.
**Esošās commentary claims** (`claim_type='commentary'`) saglabājas kā audit trail —
`speaker_id` FK paliek valid, jo commentator rindas tracked_politicians paliek (tikai
`relationship_type` mainās uz `'inactive'`).

**Profila lapa** ieguva jaunu **X subtabu**, kas rāda twitter + x_mention dokumentus,
kuros politiķis ir subject vai mentioned. Tas aizvieto zaudēto commentary saturu
ar plašāku raw mentions plūsmu. Pithiness ranking + commentary claim ekstrakcija no
mentions ir Fāze 2, kas tiks plānota atsevišķi pēc 2-3 nedēļu novērojuma.

7 demotētie pid: 62, 169, 171, 172, 174, 175, 177.
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md wiki/CHANGELOG.md
git commit -m "docs(claude): commentator demotion notes + CHANGELOG entry"
```

---

## Task 8: Pārģenerēt + verificēt vietnē

**Files:**
- (no files modified — verification only)

- [ ] **Step 1: Pārģenerēt vietni**

Run:
```bash
PYTHONPATH=. python -c "from src.generate import generate_public_site; generate_public_site()"
```
Expected: nav errors. Output sasniedz visus ~152 politiķu profilus.

- [ ] **Step 2: Verificēt sample politicians**

Atver browseri:
- `output/atmina/politiki/kaspars-melnis.html` — sagaidi X subtabu ar Heinrih5 šorīta tvītu kā mentioned
- `output/atmina/politiki/ainars-slesers.html` — Komentāri subtabā vēsturiskie Klucis attacks; X subtabā Kurmitis tvīti
- `output/atmina/politiki/edvards-smiltens.html` — X subtabā Kurmitis_ ņirgāšanās tvīts

- [ ] **Step 3: Verificēt sitewide x.html joprojām strādā**

Atver `output/atmina/x.html` — sagaidi visus tvītus + mentions, including no demotētiem commentators kā autoriem. Sitewide skats nemainās — tikai profila skats ir bagātāks.

- [ ] **Step 4: Verificēt routine**

Run:
```bash
PYTHONPATH=. python -c "from src.routine import print_routine; print_routine()"
```
Expected:
- Solis 2 (Pozīciju analīze) — pending list neietver demotētos commentators (relationship_type='inactive' filtrē ārā)
- Visi citi soļi nemainās

- [ ] **Step 5: (Nav commit šajā soļī)**

Verifikācija ir read-only.

---

## Self-Review

**Spec coverage check:**
- A (DB migrācija 7 commentators) → Task 2 ✓
- B (matcher relay path verifikācija + re-link) → Task 3 ✓
- C (jauna X subtaba profilā) → Task 4 (data) + Task 5 (UI) + Task 6 (komentāri intro fix) ✓
- Komentāri subtabas vēsturiskā saglabāšana → Task 6 ✓ (poga conditional, intro tekstu paskaidro)
- Dokumentācijas atjaunošana → Task 7 ✓
- Verifikācija → Task 8 ✓

**Placeholder scan:** Nav TBD/TODO/skipped steps. Visu kodu blokos rakstīts pilnā mērā.

**Type/name consistency:**
- `COMMENTATOR_IDS = [62, 169, 171, 172, 174, 175, 177]` lietots vienādi visā Task 2 + Task 3.
- `demote_commentators(con, only_ids=...)` testos un skriptā saglabā paraksta saderību.
- `remove_subject_links_for_demoted(con, demoted_pids=...)` saglabājas.
- `x_posts` key konsekventi izmantots Task 4 fetcher + Task 5 template.

**Gaps:** Nav. Plāns ir paš-pietiekošs.

---

## Riska reģistrs

1. **Re-link kavējas vai netiek atrasti pareizi politiķi** — `link_politicians_to_documents` izmanto `match_politicians()`. Ja matcher nepieprasīja `Melni` no `Lūgums @ltvzinas par Melni`, mēs paliksim ar dažiem orphan dokumentiem. Mitigācija: Task 3 Step 6 manuāli verificē sample case (doc 25608).

2. **`relationship_type='inactive'` ietekmē esošos vaicājumus** — `inactive` jau eksistē kā statuss, kuru filtrē generate.py un routine.py. Ja kāds skripts paļaujas uz `relationship_type='commentator'` filtru (pretēji), tas pārtrūks. Mitigācija: grep `'commentator'` pirms migrācijas; pārliecinies, ka tikai `get_pending_politicians`, `_fetch_politician_detail`, un commentary claim extraction vietas to mēģina filtrēt — visi šie cieš no commentator > inactive maiņas neutral way.

3. **9 vēsturiskās commentary claims tagad rāda speakeru kā 'inactive'** — ja UI atklāj relationship_type vērtību, vecās commentary claims rādīs commentator kā inactive (mulsinoši). Mitigācija: pārbaudi `commentary_about` query — tas izmanto `speaker_handle` un `speaker_name`, ne `relationship_type`. Cards rāda handle + name, nevis statusu — ietekmes nav.

4. **`fetch_all_twitter` pēc demotēšanas mēģina ielādēt komentētāju feeds — vai turpina?** — `social_accounts` rinda paliek `active=1` ar `feed_type='relay'`. `fetch_all_twitter` iterē `social_accounts WHERE platform='twitter' AND active=1`. Tas tomēr joprojām fetchos demotēto handle feeds. Iekšā `_store_tweets` redz `feed_type='relay'` un izvēlas relay path. Tas ir GAIDĪTS — gribam turpināt ielādēt viņu tvītus, tikai bez subject links.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-25-commentator-demotion.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
