# X profilu konsolidācija + external_profiles tabula — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Atrisināt `social_accounts` tabulas piesārņojumu (FB/website rindas + literāli X dublikāti), izveidot atsevišķu `external_profiles` tabulu Facebook/website saitēm ar fetcher-ready shēmu, atspoguļot tās politiķa profila lapā un reklasificēt `realNepareizais` (commentator) + `KNL_LTV1` (journalist + relay).

**Architecture:** Trīs slāņi. (1) DB migrācija idempotenti `src/db.py::init_db()` blokā (esošais paraugs no `feed_type` migrācijas db.py:453-465). (2) `external_profiles` tabula ir struktūras dvīnis `social_accounts` + papildus `url` lauks — paliek fetch-ready (last_fetched, last_post_id, active), bet pagaidām nav fetcher koda. (3) `social_accounts` no šī brīža tikai X (`platform='twitter'`) ar UNIQUE indeksu. Politiķa lapas template iegūst jaunu "Citi profili" mikrobloku.

**Tech Stack:** SQLite (WAL) + idempotentas ALTER/CREATE init_db blokā · Jinja2 templates · pytest (esošais `tests/test_db.py` + `tests/test_generate.py` paraugi).

---

## Failu struktūra

**Modificējami:**
- `src/db.py:439-484` — pievienot migrāciju bloku starp `feed_type` un `speaker_id` blokiem (saglabā chronological pattern)
- `src/generate.py:1326-1384` — `_fetch_politician_detail` paplašināt ar `external_profiles` query
- `templates/politician.html.j2:23-29` — pievienot `Citi profili` ikonu kopu `profile-links` div-ā
- `CLAUDE.md` — §12 invariants atjaunināt: `social_accounts` tagad satur tikai X kontus
- `tests/test_db.py` — migrācijas idempotences tests
- `tests/test_generate.py` — `_fetch_politician_detail` external_profiles atgriešanas tests

**Jauni:**
- `scripts/migrate_external_profiles.py` — vienreizējs idempotents skripts, kas pārvieto FB+website rindas + dedupē 2 X dublikātus + reklasificē 2 personas. Drīkst palaist atkārtoti — visas operācijas ir conditional.
- `tests/test_migrate_external_profiles.py` — skripta tests pret pagaidu DB

---

## Task 1: Migrācija — pievienot `external_profiles` tabulu init_db blokā

**Files:**
- Modify: `src/db.py:465` (pievienot pēc `feed_type` indeksa, pirms `speaker_id` bloka)
- Test: `tests/test_db.py`

- [ ] **Step 1: Uzrakstīt failējošu testu**

Pievienot failā `tests/test_db.py` (jaunajā vietā, blakus citiem schema testiem):

```python
def test_init_db_creates_external_profiles_table(tmp_path):
    """init_db izveido external_profiles tabulu ar pareizo shēmu."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    cols = {row[1] for row in db.execute("PRAGMA table_info(external_profiles)").fetchall()}
    assert cols == {
        "id", "opponent_id", "platform", "url", "handle",
        "display_label", "last_fetched", "last_post_id",
        "active", "notes", "created_at",
    }
    # UNIQUE constraint
    idx_rows = db.execute("PRAGMA index_list(external_profiles)").fetchall()
    idx_names = {r[1] for r in idx_rows}
    assert "idx_external_profiles_opp" in idx_names
    db.close()


def test_init_db_external_profiles_idempotent(tmp_path):
    """Otrais init_db izsaukums nepalielina rindu skaitu."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    db.execute(
        "INSERT INTO external_profiles (opponent_id, platform, url) VALUES (?, ?, ?)",
        (1, "facebook", "https://facebook.com/test"),
    )
    db.commit()
    db.close()
    init_db(db_path)  # second run must not drop
    db = get_db(db_path)
    n = db.execute("SELECT COUNT(*) FROM external_profiles").fetchone()[0]
    assert n == 1
    db.close()
```

- [ ] **Step 2: Palaist testu, lai pārliecinātos, ka tas neizdodas**

Palaist: `python -m pytest tests/test_db.py::test_init_db_creates_external_profiles_table -v`

Sagaidāmais rezultāts: `FAIL` ar `sqlite3.OperationalError: no such table: external_profiles`.

- [ ] **Step 3: Pievienot migrācijas bloku `init_db`**

Failā `src/db.py`, pēc rindas 465 (`CREATE INDEX ... idx_social_feed_type`), pievienot:

```python
    # 2026-04-25 — external_profiles tabula glabā ne-X (Facebook, website, YouTube
    # u.c.) profilus, ko politiķim varam parādīt UI un, vēlāk, fetchot. Atdalīta
    # no social_accounts, jo (a) social_accounts no šī brīža ir TIKAI X, (b) FB
    # rindas social_accounts tabulā nekad nav fetchotas (last_fetched IS NULL
    # visiem 18 ierakstiem) un piesārņoja unikalitātes statistiku. Schēma ir
    # paralēla social_accounts + papildus 'url' lauks, lai website rindām
    # 'handle' var palikt None.
    db.execute("""
        CREATE TABLE IF NOT EXISTS external_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opponent_id INTEGER NOT NULL REFERENCES tracked_politicians(id),
            platform TEXT NOT NULL,
            url TEXT NOT NULL,
            handle TEXT,
            display_label TEXT,
            last_fetched TIMESTAMP,
            last_post_id TEXT,
            active BOOLEAN DEFAULT TRUE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(opponent_id, platform, url)
        )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_external_profiles_opp "
        "ON external_profiles(opponent_id)"
    )
```

- [ ] **Step 4: Palaist testu, lai pārliecinātos, ka tas iziet**

Palaist: `python -m pytest tests/test_db.py::test_init_db_creates_external_profiles_table tests/test_db.py::test_init_db_external_profiles_idempotent -v`

Sagaidāmais rezultāts: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -m "$(cat <<'EOF'
feat(db): add external_profiles table for non-X political profiles

Separates FB/website/YouTube handles from social_accounts (which from now
on holds only X). Schema is fetch-ready (last_fetched, last_post_id) for
future per-platform fetchers; current rows just feed UI.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Migrācijas skripts — uzrakstīt failējošu testu

**Files:**
- Create: `tests/test_migrate_external_profiles.py`

- [ ] **Step 1: Uzrakstīt testus**

Izveidot failu `tests/test_migrate_external_profiles.py`:

```python
"""Tests for scripts/migrate_external_profiles.py — idempotent one-shot migration."""
import sqlite3
import pytest


@pytest.fixture
def fresh_db(tmp_path):
    """Migrētspējīga DB ar mazu paraugu social_accounts datiem."""
    from src.db import init_db, get_db
    db_path = str(tmp_path / "atmina.db")
    init_db(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (10, 'Test FB', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (20, 'Test X Dup', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (62, 'Nepareizais', 'inactive')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (59, 'KNL', 'inactive')")
    # FB row → must move to external_profiles
    db.execute("INSERT INTO social_accounts (opponent_id, platform, handle, active) VALUES (10, 'facebook', 'edvins.snore', 1)")
    # website row with URL stuffed into handle → must move + url filled
    db.execute("INSERT INTO social_accounts (opponent_id, platform, handle, active) VALUES (10, 'website', 'https://rihardskols.lv', 1)")
    # X duplicate
    db.execute("INSERT INTO social_accounts (opponent_id, platform, handle, active, last_post_id, feed_type) VALUES (20, 'twitter', 'AinarsSlesers', 1, NULL, 'first_party')")
    db.execute("INSERT INTO social_accounts (opponent_id, platform, handle, active, last_post_id, feed_type) VALUES (20, 'twitter', 'AinarsSlesers', 1, '17890', 'first_party')")
    # X normal — must stay
    db.execute("INSERT INTO social_accounts (opponent_id, platform, handle, active, feed_type) VALUES (62, 'twitter', 'realNepareizais', 0, 'first_party')")
    db.execute("INSERT INTO social_accounts (opponent_id, platform, handle, active, feed_type) VALUES (59, 'twitter', 'KNL_LTV1', 0, 'first_party')")
    db.commit()
    db.close()
    return db_path


def test_migration_moves_facebook_rows(fresh_db):
    from scripts.migrate_external_profiles import run_migration
    run_migration(fresh_db)
    db = sqlite3.connect(fresh_db)
    db.row_factory = sqlite3.Row
    fb = db.execute(
        "SELECT * FROM external_profiles WHERE platform='facebook' AND opponent_id=10"
    ).fetchall()
    assert len(fb) == 1
    assert fb[0]["handle"] == "edvins.snore"
    assert fb[0]["url"] == "https://www.facebook.com/edvins.snore"
    # Should be removed from social_accounts
    sa_fb = db.execute("SELECT COUNT(*) FROM social_accounts WHERE platform='facebook'").fetchone()[0]
    assert sa_fb == 0
    db.close()


def test_migration_moves_website_rows(fresh_db):
    from scripts.migrate_external_profiles import run_migration
    run_migration(fresh_db)
    db = sqlite3.connect(fresh_db)
    db.row_factory = sqlite3.Row
    w = db.execute(
        "SELECT * FROM external_profiles WHERE platform='website' AND opponent_id=10"
    ).fetchall()
    assert len(w) == 1
    assert w[0]["url"] == "https://rihardskols.lv"
    assert w[0]["handle"] is None  # URL nepiebāzts kā handle
    sa_w = db.execute("SELECT COUNT(*) FROM social_accounts WHERE platform='website'").fetchone()[0]
    assert sa_w == 0
    db.close()


def test_migration_dedupes_x_keeping_richer_row(fresh_db):
    from scripts.migrate_external_profiles import run_migration
    run_migration(fresh_db)
    db = sqlite3.connect(fresh_db)
    rows = db.execute(
        "SELECT last_post_id FROM social_accounts WHERE handle='AinarsSlesers'"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "17890"  # palicis bagātākais ieraksts
    db.close()


def test_migration_reclassifies_nepareizais_and_knl(fresh_db):
    from scripts.migrate_external_profiles import run_migration
    run_migration(fresh_db)
    db = sqlite3.connect(fresh_db)
    db.row_factory = sqlite3.Row
    nep = db.execute("SELECT relationship_type FROM tracked_politicians WHERE id=62").fetchone()
    assert nep["relationship_type"] == "commentator"
    nep_sa = db.execute("SELECT active, feed_type FROM social_accounts WHERE handle='realNepareizais'").fetchone()
    assert nep_sa["active"] == 1
    assert nep_sa["feed_type"] == "first_party"

    knl = db.execute("SELECT relationship_type FROM tracked_politicians WHERE id=59").fetchone()
    assert knl["relationship_type"] == "journalist"
    knl_sa = db.execute("SELECT active, feed_type FROM social_accounts WHERE handle='KNL_LTV1'").fetchone()
    assert knl_sa["active"] == 1
    assert knl_sa["feed_type"] == "relay"
    db.close()


def test_migration_is_idempotent(fresh_db):
    from scripts.migrate_external_profiles import run_migration
    run_migration(fresh_db)
    run_migration(fresh_db)  # otrā reize neko nemaina
    db = sqlite3.connect(fresh_db)
    fb_count = db.execute("SELECT COUNT(*) FROM external_profiles WHERE platform='facebook'").fetchone()[0]
    assert fb_count == 1  # nav dublēts
    sa_dups = db.execute("SELECT COUNT(*) FROM social_accounts WHERE handle='AinarsSlesers'").fetchone()[0]
    assert sa_dups == 1
    db.close()


def test_migration_adds_unique_index_on_social_accounts(fresh_db):
    from scripts.migrate_external_profiles import run_migration
    run_migration(fresh_db)
    db = sqlite3.connect(fresh_db)
    idx = db.execute("PRAGMA index_list(social_accounts)").fetchall()
    names = {r[1] for r in idx}
    assert "idx_social_accounts_unique" in names
    # Pārbaude — unique index novērš atkārtotu insert
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (62, 'twitter', 'realNepareizais')"
        )
        db.commit()
    db.close()
```

- [ ] **Step 2: Palaist testus, lai pārliecinātos, ka tie neizdodas**

Palaist: `python -m pytest tests/test_migrate_external_profiles.py -v`

Sagaidāmais rezultāts: visi 6 testi `FAIL` ar `ModuleNotFoundError: No module named 'scripts.migrate_external_profiles'`.

- [ ] **Step 3: Commit testu fails**

```bash
git add tests/test_migrate_external_profiles.py
git commit -m "test(migrate): failing tests for external_profiles migration script

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Migrācijas skripts — implementēt

**Files:**
- Create: `scripts/migrate_external_profiles.py`

- [ ] **Step 1: Implementēt skriptu**

Izveidot failu `scripts/migrate_external_profiles.py`:

```python
"""One-shot idempotent migration: konsolidē social_accounts un izveido external_profiles.

Operācijas (visas conditional → drīkst palaist atkārtoti):
  1. Pārvieto platform IN ('facebook','website') rindas no social_accounts uz
     external_profiles. URL veidots:
       - facebook: https://www.facebook.com/{handle}
       - website: handle pats ir URL → url=handle, handle=NULL
  2. Dedupē literālus X dublikātus (paturot rindu ar non-NULL last_post_id, vai
     jaunāku last_fetched, vai mazāku id kā tiebreaker).
  3. Pievieno UNIQUE index uz social_accounts(opponent_id, platform, handle).
  4. Reklasificē:
       - id=62 (realNepareizais): tracked_politicians.relationship_type='commentator',
         social_accounts.active=1, feed_type='first_party'.
       - id=59 (KNL_LTV1): tracked_politicians.relationship_type='journalist',
         social_accounts.active=1, feed_type='relay'.

Usage:
    python -m scripts.migrate_external_profiles
    python -m scripts.migrate_external_profiles --db data/atmina.db
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _migrate_facebook_rows(db: sqlite3.Connection) -> int:
    """Pārvieto FB rindas. Atgriež pārvietoto skaitu."""
    rows = db.execute(
        "SELECT id, opponent_id, handle, last_fetched, last_post_id, active "
        "FROM social_accounts WHERE platform='facebook'"
    ).fetchall()
    moved = 0
    for r in rows:
        url = f"https://www.facebook.com/{r[2]}" if r[2] else None
        if not url:
            continue
        db.execute(
            "INSERT OR IGNORE INTO external_profiles "
            "(opponent_id, platform, url, handle, last_fetched, last_post_id, active) "
            "VALUES (?, 'facebook', ?, ?, ?, ?, ?)",
            (r[1], url, r[2], r[3], r[4], r[5]),
        )
        db.execute("DELETE FROM social_accounts WHERE id=?", (r[0],))
        moved += 1
    return moved


def _migrate_website_rows(db: sqlite3.Connection) -> int:
    """Pārvieto website rindas (handle satur URL)."""
    rows = db.execute(
        "SELECT id, opponent_id, handle, last_fetched, last_post_id, active "
        "FROM social_accounts WHERE platform='website'"
    ).fetchall()
    moved = 0
    for r in rows:
        url = r[2]
        if not url:
            continue
        db.execute(
            "INSERT OR IGNORE INTO external_profiles "
            "(opponent_id, platform, url, handle, last_fetched, last_post_id, active) "
            "VALUES (?, 'website', ?, NULL, ?, ?, ?)",
            (r[1], url, r[3], r[4], r[5]),
        )
        db.execute("DELETE FROM social_accounts WHERE id=?", (r[0],))
        moved += 1
    return moved


def _dedupe_x_handles(db: sqlite3.Connection) -> int:
    """Dedupē literālus X dublikātus. Patur rindu ar non-NULL last_post_id;
    citādi rindu ar jaunāku last_fetched; citādi mazāko id."""
    dups = db.execute(
        "SELECT opponent_id, handle FROM social_accounts "
        "WHERE platform='twitter' "
        "GROUP BY opponent_id, handle HAVING COUNT(*) > 1"
    ).fetchall()
    deleted = 0
    for opp_id, handle in dups:
        rows = db.execute(
            "SELECT id, last_post_id, last_fetched FROM social_accounts "
            "WHERE platform='twitter' AND opponent_id=? AND handle=? "
            "ORDER BY (last_post_id IS NULL) ASC, last_fetched DESC, id ASC",
            (opp_id, handle),
        ).fetchall()
        keep_id = rows[0][0]
        for r in rows[1:]:
            db.execute("DELETE FROM social_accounts WHERE id=?", (r[0],))
            deleted += 1
        logger.info("Dedupe %s (opp=%s): kept id=%s, removed %d", handle, opp_id, keep_id, len(rows) - 1)
    return deleted


def _add_social_accounts_unique_index(db: sqlite3.Connection) -> None:
    """UNIQUE index uz (opponent_id, platform, handle).

    PIRMS šī izsaukuma _dedupe_x_handles JĀBŪT pabeigtam — citādi indeks
    crashēs. Idempotents — IF NOT EXISTS.
    """
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_social_accounts_unique "
        "ON social_accounts(opponent_id, platform, handle)"
    )


def _reclassify_nepareizais(db: sqlite3.Connection) -> bool:
    """tracked_politicians.id=62 → commentator; social_accounts → active=1."""
    cur = db.execute(
        "UPDATE tracked_politicians SET relationship_type='commentator' "
        "WHERE id=62 AND relationship_type != 'commentator'"
    )
    changed_tp = cur.rowcount > 0
    cur = db.execute(
        "UPDATE social_accounts SET active=1, feed_type='first_party' "
        "WHERE opponent_id=62 AND handle='realNepareizais' "
        "AND (active=0 OR feed_type != 'first_party')"
    )
    changed_sa = cur.rowcount > 0
    return changed_tp or changed_sa


def _reclassify_knl(db: sqlite3.Connection) -> bool:
    """tracked_politicians.id=59 → journalist; social_accounts → relay+active."""
    cur = db.execute(
        "UPDATE tracked_politicians SET relationship_type='journalist' "
        "WHERE id=59 AND relationship_type != 'journalist'"
    )
    changed_tp = cur.rowcount > 0
    cur = db.execute(
        "UPDATE social_accounts SET active=1, feed_type='relay' "
        "WHERE opponent_id=59 AND handle='KNL_LTV1' "
        "AND (active=0 OR feed_type != 'relay')"
    )
    changed_sa = cur.rowcount > 0
    return changed_tp or changed_sa


def run_migration(db_path: str) -> dict:
    """Izpilda visas operācijas vienā transakcijā. Idempotents."""
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys = ON")
    try:
        # Sagatavošanās — pārliecināmies, ka external_profiles eksistē
        # (init_db jau būs to izveidojusi, bet ja palaiž skriptu pirms init,
        # kļūdas message ir skaidrāks).
        cur = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='external_profiles'"
        ).fetchone()
        if not cur:
            raise RuntimeError(
                "external_profiles tabula nav atrasta — palaidiet init_db pirms migrācijas"
            )

        fb_moved = _migrate_facebook_rows(db)
        web_moved = _migrate_website_rows(db)
        dedup = _dedupe_x_handles(db)
        _add_social_accounts_unique_index(db)
        nep_changed = _reclassify_nepareizais(db)
        knl_changed = _reclassify_knl(db)

        db.commit()
        result = {
            "facebook_moved": fb_moved,
            "website_moved": web_moved,
            "x_duplicates_removed": dedup,
            "nepareizais_reclassified": nep_changed,
            "knl_reclassified": knl_changed,
        }
        logger.info("Migration complete: %s", result)
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/atmina.db", help="DB ceļš")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not Path(args.db).exists():
        logger.error("DB not found: %s", args.db)
        return 1

    result = run_migration(args.db)
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Palaist testus**

Palaist: `python -m pytest tests/test_migrate_external_profiles.py -v`

Sagaidāmais rezultāts: visi 6 testi `PASS`.

- [ ] **Step 3: Commit**

```bash
git add scripts/migrate_external_profiles.py
git commit -m "$(cat <<'EOF'
feat(migrate): script consolidating social_accounts → X-only + external_profiles

Idempotent one-shot:
  - Moves 18 FB + 5 website rows from social_accounts to external_profiles
  - Dedupes 2 literal X duplicates (AinarsSlesers ×2, suvajevs ×2)
  - Adds UNIQUE(opponent_id, platform, handle) on social_accounts
  - Reclassifies realNepareizais → commentator, KNL_LTV1 → journalist+relay

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Palaist migrāciju pret reālo DB ar backup

**Files:** _(rīcība, ne kods)_

- [ ] **Step 1: Izveidot DB backup**

```bash
cp data/atmina.db data/atmina_backup_pre_external_profiles.db
```

- [ ] **Step 2: Pārliecināties, ka init_db ir palaists (lai eksistē external_profiles)**

```bash
python -c "from src.db import init_db; init_db()"
```

- [ ] **Step 3: Palaist migrāciju**

```bash
python -m scripts.migrate_external_profiles --db data/atmina.db -v
```

Sagaidāmais output (rindas skaits no audita 2026-04-25):
```
{'facebook_moved': 18, 'website_moved': 5, 'x_duplicates_removed': 2,
 'nepareizais_reclassified': True, 'knl_reclassified': True}
```

- [ ] **Step 4: Verificēt rezultātus DB**

```bash
python -c "
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
db = sqlite3.connect('data/atmina.db')
print('social_accounts platforms:', db.execute('SELECT platform, COUNT(*) FROM social_accounts GROUP BY platform').fetchall())
print('external_profiles platforms:', db.execute('SELECT platform, COUNT(*) FROM external_profiles GROUP BY platform').fetchall())
print('Nepareizais (62):', db.execute('SELECT relationship_type FROM tracked_politicians WHERE id=62').fetchone())
print('KNL (59):', db.execute('SELECT relationship_type FROM tracked_politicians WHERE id=59').fetchone())
print('KNL feed_type:', db.execute(\"SELECT feed_type, active FROM social_accounts WHERE handle='KNL_LTV1'\").fetchone())
"
```

Sagaidāmais output:
```
social_accounts platforms: [('twitter', 59)]
external_profiles platforms: [('facebook', 18), ('website', 5)]
Nepareizais (62): ('commentator',)
KNL (59): ('journalist',)
KNL feed_type: ('relay', 1)
```

- [ ] **Step 5: Palaist otrreiz, lai apstiprinātu idempotenci**

```bash
python -m scripts.migrate_external_profiles --db data/atmina.db -v
```

Sagaidāmais output:
```
{'facebook_moved': 0, 'website_moved': 0, 'x_duplicates_removed': 0,
 'nepareizais_reclassified': False, 'knl_reclassified': False}
```

- [ ] **Step 6: Commit migrācijas izpildes faktu (DB ir gitignored, šis ir tikai marker commit)**

Šis solis tikai dokumentē migrāciju git žurnālā — DB izmaiņām nav diff. Pievienot piezīmi `wiki/CHANGELOG.md`:

Failā `wiki/CHANGELOG.md`, top of file (pēc esošā header), pievienot:

```markdown
## 2026-04-25 — social_accounts → X-only + external_profiles

`social_accounts` tabula tagad satur tikai aktīvus X kontus (vienu uz politiķi —
UNIQUE constraint). FB (18) un website (5) rindas pārceltas uz jauno
`external_profiles` tabulu (fetcher-ready shēma, pagaidām bez fetcher koda).
Reklasificēti: `realNepareizais` → commentator (analogs Kļuciņam), `KNL_LTV1`
→ journalist ar `feed_type='relay'` (analogs LTV Ziņas pattern).

Migrācija: `scripts/migrate_external_profiles.py` (idempotents). Backup pirms
migrācijas: `data/atmina_backup_pre_external_profiles.db`.
```

```bash
git add wiki/CHANGELOG.md
git commit -m "docs(changelog): 2026-04-25 social_accounts X-only + external_profiles

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Paplašināt `_fetch_politician_detail` ar external_profiles

**Files:**
- Modify: `src/generate.py:1326-1384` (pievienot query + return key)
- Test: `tests/test_generate.py`

- [ ] **Step 1: Uzrakstīt failējošu testu**

Pievienot failā `tests/test_generate.py`:

```python
def test_fetch_politician_detail_includes_external_profiles(tmp_path):
    """_fetch_politician_detail atgriež 'external_profiles' atslēgu ar FB/website rindām."""
    from src.db import init_db, get_db
    from src.generate import _fetch_politician_detail
    db_path = str(tmp_path / "atmina.db")
    init_db(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id, name) VALUES (10, 'Test')")
    db.execute(
        "INSERT INTO external_profiles (opponent_id, platform, url, handle, active) "
        "VALUES (10, 'facebook', 'https://www.facebook.com/test.user', 'test.user', 1)"
    )
    db.execute(
        "INSERT INTO external_profiles (opponent_id, platform, url, active) "
        "VALUES (10, 'website', 'https://testsite.lv', 1)"
    )
    db.execute(
        "INSERT INTO external_profiles (opponent_id, platform, url, active) "
        "VALUES (10, 'website', 'https://oldsite.lv', 0)"
    )
    db.commit()
    detail = _fetch_politician_detail(db, 10)
    profiles = detail["external_profiles"]
    assert len(profiles) == 2  # tikai aktīvie
    platforms = {p["platform"] for p in profiles}
    assert platforms == {"facebook", "website"}
    fb = next(p for p in profiles if p["platform"] == "facebook")
    assert fb["url"] == "https://www.facebook.com/test.user"
    assert fb["handle"] == "test.user"
    db.close()
```

- [ ] **Step 2: Palaist testu, lai pārliecinātos, ka tas neizdodas**

Palaist: `python -m pytest tests/test_generate.py::test_fetch_politician_detail_includes_external_profiles -v`

Sagaidāmais rezultāts: `FAIL` ar `KeyError: 'external_profiles'`.

- [ ] **Step 3: Pievienot query un return atslēgu**

Failā `src/generate.py`, atrast `_fetch_politician_detail` (rinda 1326). Tieši pirms `return` paziņojuma (kur tas atgriežas — atrodams uz `return {`), pievienot:

```python
    # External profiles (FB, website, ...) — fetch-ready shēma, pagaidām tikai UI.
    ext_rows = db.execute(
        "SELECT platform, url, handle, display_label "
        "FROM external_profiles WHERE opponent_id=? AND active=1 "
        "ORDER BY platform, id",
        (pid,),
    ).fetchall()
    external_profiles = [dict(r) for r in ext_rows]
```

Pēc tam pievienot `"external_profiles": external_profiles,` `return {...}` blokā.

- [ ] **Step 4: Palaist testu**

Palaist: `python -m pytest tests/test_generate.py::test_fetch_politician_detail_includes_external_profiles -v`

Sagaidāmais rezultāts: `PASS`.

- [ ] **Step 5: Commit**

```bash
git add src/generate.py tests/test_generate.py
git commit -m "feat(generate): expose external_profiles in politician detail

Profile pages now load active FB/website/etc. rows alongside the X handle.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Atspoguļot external_profiles politiķa lapā

**Files:**
- Modify: `templates/politician.html.j2:23-29` (`profile-links` div)

- [ ] **Step 1: Pievienot ikonas blokus pēc esošā X icon**

Failā `templates/politician.html.j2`, atrast `profile-links` div (rindas 23-29) un atjaunināt:

```jinja2
          <div class="profile-links">
            {% if politician.x_handle %}
            <a href="https://x.com/{{ politician.x_handle }}" target="_blank" rel="noopener" title="@{{ politician.x_handle }}">
              <svg viewBox="0 0 24 24" class="profile-link-icon"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
            </a>
            {% endif %}
            {% for ep in external_profiles %}
              {% if ep.platform == 'facebook' %}
              <a href="{{ ep.url | safe_url }}" target="_blank" rel="noopener" title="Facebook: {{ ep.handle or ep.url }}">
                <svg viewBox="0 0 24 24" class="profile-link-icon" aria-hidden="true"><path d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12z"/></svg>
              </a>
              {% elif ep.platform == 'website' %}
              <a href="{{ ep.url | safe_url }}" target="_blank" rel="noopener" title="Tīmekļa lapa: {{ ep.url }}">
                <svg viewBox="0 0 24 24" class="profile-link-icon" aria-hidden="true"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm7.93 9h-3.04a15.5 15.5 0 0 0-1.2-5.32A8.03 8.03 0 0 1 19.93 11zM12 4c1.36 1.97 2.16 4.36 2.36 7H9.64C9.84 8.36 10.64 5.97 12 4zM4.07 13h3.04c.13 1.84.55 3.65 1.2 5.32A8.03 8.03 0 0 1 4.07 13zm0-2A8.03 8.03 0 0 1 8.31 5.68 15.5 15.5 0 0 0 7.11 11H4.07zM12 20c-1.36-1.97-2.16-4.36-2.36-7h4.72c-.2 2.64-1 5.03-2.36 7zm3.69-1.68c.65-1.67 1.07-3.48 1.2-5.32h3.04a8.03 8.03 0 0 1-4.24 5.32z"/></svg>
              </a>
              {% endif %}
            {% endfor %}
          </div>
```

- [ ] **Step 2: Pievienot template kontekstam (generate.py rindā 3238)**

Failā `src/generate.py`, atrast `_render_page(env, "politician.html.j2", ...)` (rinda 3238) un pievienot `external_profiles` kontekstam:

```python
        _render_page(env, "politician.html.j2", politiki_dir / f"{p['slug']}.html", {
            "politician": p,
            "claims": detail["claims"],
            "positions": detail["positions"],
            "contradictions": detail["contradictions"],
            "votes": detail["votes"],
            "claim_topics": detail["claim_topics"],
            "timeline": detail["timeline"],
            "tensions": detail["tensions"],
            "news": detail["news"],
            "party_meta": detail["party_meta"],
            "commentary_about": detail["commentary_about"],
            "external_profiles": detail["external_profiles"],
            "wiki_profile": wiki_profile,
            "has_photo": has_photo,
            "syntheses": pid_to_syntheses.get(p["id"], []),
        })
```

- [ ] **Step 3: Smoke render — palaist site generation un atvērt vienu profilu pārlūkā**

```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

Manuāli atvērt `output/atmina/politiki/edvins-snore.html` pārlūkā (Snore ir FB rindā audita rezultātos). Sagaidāms: blakus X ikonai parādās zila FB ikona, kas atver `https://www.facebook.com/edvins.snore`. Gadījumā ja izmaiņas neiet cauri — pārbaudīt vai `external_profiles` ir tukšs `_fetch_politician_detail` rezultātā (likely DB nav migrēta).

- [ ] **Step 4: Commit**

```bash
git add templates/politician.html.j2 src/generate.py
git commit -m "$(cat <<'EOF'
feat(profile): render external_profiles (FB, website) icons on politician page

Adds Facebook and generic-website icons to profile-links row, sourced from
external_profiles table. Inactive rows are filtered upstream in
_fetch_politician_detail.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Atjaunināt CLAUDE.md §12 — vienteikuma prefikss

**Files:**
- Modify: `CLAUDE.md` — §12 (Social feed_type)

**Pamatojums (pārrunāts 2026-04-25):** §12 nav jāsadala 12+12a. X-only invariants ir vienteikuma prefikss esošajam §12, jo CLAUDE.md kritērijs ir "datu-integritātes invariants" — un tāds ir tikai viens (FB/website nedrīkst atgriezties `social_accounts`). Pārējais (skripts, datu fix, schema rationale) paliek CHANGELOG'ā un `db.py` schema komentārā. Bez jauna wiki faila.

- [ ] **Step 1: Atjaunināt §12 in-place**

Failā `CLAUDE.md`, atrast §12 sākumu un aizvietot pirmo teikumu.

Pirms:
```markdown
12. **`social_accounts.feed_type` classifies X accounts as `'first_party'` (default) or `'relay'`.**
```

Pēc:
```markdown
12. **`social_accounts` glabā tikai aktīvus X kontus, vienu uz politiķi** (UNIQUE `(opponent_id, platform, handle)`; FB/website → `external_profiles`). **`feed_type` classifies X accounts as `'first_party'` (default) or `'relay'`.**
```

Pārējais §12 saturs (first-party speaker behavior + relay matcher pattern + CHANGELOG breadcrumb) paliek nemainīgs.

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): §12 prefix — social_accounts X-only invariant

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Pilna testu sērija + smoke

**Files:** _(verifikācija)_

- [ ] **Step 1: Palaist visu testu komplektu**

```bash
python -m pytest tests/ -v
```

Sagaidāmais rezultāts: visi testi `PASS`. Ja kaut kas crashē, sniegt failed-test izvadi pirms commit.

- [ ] **Step 2: Smoke — pilna site generēšana**

```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

Sagaidāms: bez crash, `output/atmina/` saglabā svaigu HTML kopu. Manuāli pārbaudīt vismaz 2 profilus, kuriem zināmi external profiles:
  - `output/atmina/politiki/edvins-snore.html` (FB)
  - `output/atmina/politiki/rihards-kols.html` (website)

- [ ] **Step 3: Routine status**

```bash
python -c "from src.routine import print_routine; print_routine()"
```

Sagaidāms: nav `social_accounts` warningu (UNIQUE indekss + 59 X rindas).

---

## Self-review checklist

**Spec coverage** — visi 4 brief.md punkti aptver:
1. ✅ Cross-platform debris cleanup → Task 1-4
2. ✅ FB atsevišķā tabulā nākotnes fetcham → Task 1 (external_profiles ar last_fetched)
3. ✅ Komentētāju reklasifikācija → Task 3 (`_reclassify_nepareizais`, `_reclassify_knl`)
4. ✅ Display politiķa lapā → Task 5-6

**Type consistency** — `external_profiles` lauks `url` (NOT NULL) + `handle` (nullable) lietots konsekventi: migrācijas skripts ievada abus, `_fetch_politician_detail` atgriež abus, template lieto abus.

**Commentator weight** (no brief'a §4 vēlāk-bloka) ir TĪŠI atstāts ārpus šī plāna — implementēsim, kad faktiski būs 4+ commentators. Tagad tikai 2 (Kļuciņš + Nepareizais), tāpēc YAGNI.

---

## Execution Handoff

Plāns gatavs un saglabāts `docs/superpowers/plans/2026-04-25-x-profilu-konsolidacija.md`. Divas izpildes opcijas:

**1. Subagent-Driven (rekomendēts)** — es dispatchoju svaigu subagent katram task'am, review starp tasku, ātra iterācija.

**2. Inline Execution** — izpildām šajā sesijā, izmantojot `superpowers:executing-plans`, batch ar checkpointiem.

Kuru pieeju izvēlies?
