# atmina Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the atmina political transparency platform by migrating the proven politracker pipeline to a clean new project, stripping campaign-specific code, and adding a static site generator for atmina.lv.

**Architecture:** Migrate SQLite DB + Python scraping/analysis pipeline from politracker. Strip MMN campaign artifacts. Add static site generator (Jinja2 → HTML). Redesign wiki for frontmatter-only sync. All code lives in `~\atmina\`.

**Tech Stack:** Python 3.11+, SQLite + sqlite-vec, Pydantic v2, Jinja2, httpx, trafilatura, twikit, sentence-transformers, Chart.js, markdown.

**Source:** `~\OppTracker\politracker\` (read-only reference)
**Target:** `~\atmina\`

---

## Task 1: Project Scaffolding

Create the project structure, virtual environment, dependencies, and gitignore.

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: directory structure

- [ ] **Step 1: Create directory structure**

```bash
cd ~/atmina
mkdir -p src tests templates assets content/analizes data/saeima_votes output/atmina output/agents wiki/persons wiki/topics wiki/synthesis wiki/dailies .claude/agents
touch src/__init__.py tests/__init__.py
```

- [ ] **Step 2: Create requirements.txt**

```
# Scraping
httpx
trafilatura
beautifulsoup4
lxml
crawl4ai

# X/Twitter
twikit

# NLP
sentence-transformers
simplemma
fasttext-wheel

# Database
sqlite-vec
simhash
pydantic>=2.0

# Templates & rendering
jinja2
pyyaml
markdown

# Utilities
keyring
```

- [ ] **Step 3: Create .gitignore**

```
# Database
*.db
*.db-wal
*.db-shm
data/*.backup-*

# Auth
data/x_cookies.json

# Python
.venv/
__pycache__/
*.pyc

# Output
output/

# OS
.DS_Store
Thumbs.db

# Archives
*.gz
*.zip
*.tar.gz
```

- [ ] **Step 4: Create virtual environment and install dependencies**

```bash
cd ~/atmina
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: project scaffolding — directories, dependencies, gitignore"
```

---

## Task 2: DB Migration

Copy the politracker database, strip campaign-specific data, add 78 missing Saeima deputies, fix the saeima_votes schema.

**Files:**
- Create: `scripts/migrate_db.py`
- Create: `data/atmina.db` (generated)

- [ ] **Step 1: Create the migration script**

```python
# scripts/migrate_db.py
"""Migrate politracker.db → atmina.db
Strips campaign-specific data, adds missing Saeima deputies, fixes schema.
"""
import shutil
import sqlite3
import json
import re
import sys
from pathlib import Path

SOURCE_DB = Path(r"~\OppTracker\politracker\politracker.db")
TARGET_DB = Path(__file__).parent.parent / "data" / "atmina.db"

CAMPAIGN_PATTERNS = re.compile(
    r"MMN perspektīva|uzbrukuma leņķ|Mēs mainām noteikumus|"
    r"kampaņas|Ieteikumi kampaņai|campaign_voice|party_ideology|"
    r"MMN perspektīvā|pīlār",
    re.IGNORECASE,
)

FACTION_TO_PARTY = {
    "JV": "Jaunā Vienotība",
    "ZZS": "Zaļo un Zemnieku savienība",
    "NA": "Nacionālā apvienība",
    "PRO": "Progresīvie",
    "LPV": "Latvija Pirmajā Vietā",
    "AS": "Apvienotais saraksts",
    "LA": "Latvijas attīstībai",
    "K": "Konservatīvie",
}

COALITION_FACTIONS = {"JV", "ZZS", "PRO"}
OPPOSITION_FACTIONS = {"NA", "AS", "LPV"}


def migrate():
    print(f"Source: {SOURCE_DB}")
    print(f"Target: {TARGET_DB}")

    if not SOURCE_DB.exists():
        print("ERROR: Source DB not found!")
        sys.exit(1)

    # Step 1: Copy DB
    TARGET_DB.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_DB, TARGET_DB)
    print(f"Copied DB ({TARGET_DB.stat().st_size / 1024 / 1024:.1f} MB)")

    db = sqlite3.connect(str(TARGET_DB))
    db.execute("PRAGMA foreign_keys = OFF")  # Disable for bulk operations

    # Step 2: Delete campaign-specific tables
    deleted_briefs = db.execute("DELETE FROM oppo_briefs").rowcount
    print(f"Deleted {deleted_briefs} oppo_briefs")

    deleted_mentions = db.execute("DELETE FROM mention_classifications").rowcount
    print(f"Deleted {deleted_mentions} mention_classifications")

    # Step 3: Delete campaign-framed context notes
    # Delete ALL daily/weekly briefs (MMN-perspectived)
    deleted_briefs_notes = db.execute(
        "DELETE FROM context_notes WHERE note_type IN ('daily_brief', 'weekly_brief')"
    ).rowcount
    print(f"Deleted {deleted_briefs_notes} daily/weekly brief notes")

    # Delete context notes with campaign language
    all_notes = db.execute(
        "SELECT id, content FROM context_notes WHERE note_type IN ('context', 'event', 'polling', 'tip', 'correction')"
    ).fetchall()
    campaign_note_ids = []
    for note_id, content in all_notes:
        if content and CAMPAIGN_PATTERNS.search(content):
            campaign_note_ids.append(note_id)
    if campaign_note_ids:
        placeholders = ",".join("?" * len(campaign_note_ids))
        db.execute(f"DELETE FROM context_notes WHERE id IN ({placeholders})", campaign_note_ids)
    print(f"Deleted {len(campaign_note_ids)} campaign-framed context notes (kept {len(all_notes) - len(campaign_note_ids)} neutral)")

    # Step 4: Remove @partijaMMN social account and its documents
    mmn_account = db.execute(
        "SELECT id FROM social_accounts WHERE handle LIKE '%partijaMMN%'"
    ).fetchone()
    if mmn_account:
        mmn_acc_id = mmn_account[0]
        # Delete documents from this account
        deleted_docs = db.execute(
            "DELETE FROM documents WHERE source_url LIKE '%partijaMMN%'"
        ).rowcount
        db.execute("DELETE FROM social_accounts WHERE id = ?", (mmn_acc_id,))
        print(f"Deleted @partijaMMN account + {deleted_docs} documents")
    else:
        print("No @partijaMMN account found (already clean)")

    # Step 5: Fix saeima_votes schema — add missing columns
    for col, col_type in [("summary", "TEXT"), ("document_nr", "TEXT"),
                          ("document_url", "TEXT"), ("topic", "TEXT")]:
        try:
            db.execute(f"ALTER TABLE saeima_votes ADD COLUMN {col} {col_type}")
            print(f"Added saeima_votes.{col}")
        except Exception:
            pass  # Already exists

    # Backfill topic from motif
    # Import topic mapping keywords inline (simplified version)
    votes_to_backfill = db.execute(
        "SELECT id, motif FROM saeima_votes WHERE topic IS NULL"
    ).fetchall()
    TOPIC_KEYWORDS = {
        "aizsardzīb": "Aizsardzība un drošība", "drošīb": "Aizsardzība un drošība",
        "NATO": "Aizsardzība un drošība", "militār": "Aizsardzība un drošība",
        "Ukrain": "Ukraina un Krievija", "Kriminal": "Tieslietas",
        "budžet": "Budžets un finanses", "nodokl": "Budžets un finanses",
        "izglītīb": "Izglītība", "veselīb": "Sociālā politika",
        "enerģ": "Degviela un enerģētika", "imigrāc": "Imigrācija",
        "vēlēšan": "Vēlēšanas", "Saeimas kārtīb": "Valsts pārvalde",
        "pašvaldīb": "Pašvaldības", "transport": "Transports",
        "meža": "Mežsaimniecība", "vide": "Vide",
        "tieslietu": "Tieslietas", "likumprojekt": "Valsts pārvalde",
    }
    backfilled = 0
    for vote_id, motif in votes_to_backfill:
        topic = None
        if motif:
            motif_lower = motif.lower()
            for keyword, mapped_topic in TOPIC_KEYWORDS.items():
                if keyword.lower() in motif_lower:
                    topic = mapped_topic
                    break
            if not topic:
                topic = "Valsts pārvalde"  # Default for unmatched legislative items
            summary = motif[:200]
            db.execute(
                "UPDATE saeima_votes SET topic=?, summary=? WHERE id=?",
                (topic, summary, vote_id)
            )
            backfilled += 1
    print(f"Backfilled topic for {backfilled} votes")

    # Step 6: Add missing Saeima deputies
    unmatched = db.execute("""
        SELECT DISTINCT deputy_name, faction
        FROM saeima_individual_votes
        WHERE politician_id IS NULL
        ORDER BY faction, deputy_name
    """).fetchall()

    added = 0
    for deputy_name, faction in unmatched:
        # Check not already tracked
        existing = db.execute(
            "SELECT id FROM tracked_politicians WHERE name = ?", (deputy_name,)
        ).fetchone()
        if existing:
            continue

        party = FACTION_TO_PARTY.get(faction, "")
        if faction in COALITION_FACTIONS:
            rel_type = "coalition_partner"
        elif faction in OPPOSITION_FACTIONS:
            rel_type = "opponent"
        else:
            rel_type = "neutral"

        name_forms = [deputy_name]
        parts = deputy_name.split()
        if len(parts) == 2:
            name_forms.append(parts[1])  # Surname
            name_forms.append(f"{parts[1]}, {parts[0]}")  # Surname, Name

        db.execute("""
            INSERT INTO tracked_politicians (name, party, role, name_forms, keywords, relationship_type, notes)
            VALUES (?, ?, 'Saeimas deputāts', ?, '[]', ?, 'Auto-added from Saeima votes')
        """, (deputy_name, party, json.dumps(name_forms, ensure_ascii=False), rel_type))
        added += 1

    print(f"Added {added} Saeima deputies")

    # Step 7: Re-match individual votes to politicians
    politicians = db.execute("SELECT id, name, name_forms FROM tracked_politicians").fetchall()
    name_to_pid = {}
    for pid, name, forms_json in politicians:
        forms = json.loads(forms_json) if forms_json else [name]
        for form in forms:
            name_to_pid[form.strip().lower()] = pid

    unmatched_votes = db.execute(
        "SELECT DISTINCT deputy_name FROM saeima_individual_votes WHERE politician_id IS NULL"
    ).fetchall()
    matched = 0
    for (deputy_name,) in unmatched_votes:
        pid = name_to_pid.get(deputy_name.strip().lower())
        if pid:
            db.execute(
                "UPDATE saeima_individual_votes SET politician_id = ? WHERE deputy_name = ? AND politician_id IS NULL",
                (pid, deputy_name)
            )
            matched += 1

    print(f"Matched {matched} deputies to tracked_politicians")

    # Step 8: Verify
    db.commit()
    total_politicians = db.execute(
        "SELECT COUNT(*) FROM tracked_politicians WHERE relationship_type != 'inactive'"
    ).fetchone()[0]
    total_claims = db.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    total_contradictions = db.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0]
    total_votes = db.execute("SELECT COUNT(*) FROM saeima_votes").fetchone()[0]
    total_docs = db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    still_unmatched = db.execute(
        "SELECT COUNT(DISTINCT deputy_name) FROM saeima_individual_votes WHERE politician_id IS NULL"
    ).fetchone()[0]

    print(f"\n--- Migration Complete ---")
    print(f"Politicians: {total_politicians}")
    print(f"Documents: {total_docs}")
    print(f"Claims: {total_claims}")
    print(f"Contradictions: {total_contradictions}")
    print(f"Saeima votes: {total_votes}")
    print(f"Unmatched deputies: {still_unmatched}")

    # Step 9: VACUUM
    db.execute("VACUUM")
    db.close()
    final_size = TARGET_DB.stat().st_size / 1024 / 1024
    print(f"Final DB size: {final_size:.1f} MB")


if __name__ == "__main__":
    migrate()
```

- [ ] **Step 2: Run the migration**

```bash
cd ~/atmina
PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/migrate_db.py
```

Expected output:
- 100+ politicians
- ~920+ documents (minus partijaMMN tweets)
- ~230 claims
- 21 contradictions
- 18+ votes
- 0 or near-0 unmatched deputies

- [ ] **Step 3: Verify critical data**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
import sqlite3
db = sqlite3.connect('data/atmina.db')
# Verify no campaign data remains
briefs = db.execute('SELECT COUNT(*) FROM oppo_briefs').fetchone()[0]
mentions = db.execute('SELECT COUNT(*) FROM mention_classifications').fetchone()[0]
campaign_notes = db.execute(\"SELECT COUNT(*) FROM context_notes WHERE content LIKE '%MMN perspektīva%'\").fetchone()[0]
mmn_account = db.execute(\"SELECT COUNT(*) FROM social_accounts WHERE handle LIKE '%partijaMMN%'\").fetchone()[0]
print(f'oppo_briefs: {briefs} (should be 0)')
print(f'mention_classifications: {mentions} (should be 0)')
print(f'campaign notes remaining: {campaign_notes} (should be 0)')
print(f'partijaMMN accounts: {mmn_account} (should be 0)')
# Verify saeima schema
cols = [r[1] for r in db.execute('PRAGMA table_info(saeima_votes)').fetchall()]
assert 'topic' in cols, 'Missing topic column'
assert 'summary' in cols, 'Missing summary column'
print(f'saeima_votes columns: {cols}')
print('All checks passed!')
"
```

- [ ] **Step 4: Commit**

```bash
git add scripts/migrate_db.py
git add -f data/atmina.db
git commit -m "feat: migrate DB from politracker — cleaned, 100+ deputies, schema fixed"
```

---

## Task 3: Migrate Core Pipeline

Copy the core source files from politracker. These are nearly unchanged — the analysis pipeline is neutral.

**Files to copy from `~\OppTracker\politracker\src\`:**
- `db.py` → `src/db.py` (as-is)
- `models.py` → `src/models.py` (remove OppoBrief)
- `topic_map.py` → `src/topic_map.py` (as-is)
- `embeddings.py` → `src/embeddings.py` (as-is)
- `analyze.py` → `src/analyze.py` (as-is)
- `tools.py` → `src/tools.py` (remove store_oppo_brief, remove export_dashboard)

- [ ] **Step 1: Copy files that need no changes**

```bash
cd ~/atmina
cp "~/OppTracker/politracker/src/db.py" src/db.py
cp "~/OppTracker/politracker/src/topic_map.py" src/topic_map.py
cp "~/OppTracker/politracker/src/embeddings.py" src/embeddings.py
cp "~/OppTracker/politracker/src/analyze.py" src/analyze.py
```

- [ ] **Step 2: Copy and clean models.py**

Copy `models.py`, then remove the `OppoBrief` class (campaign-specific opposition brief model). Keep everything else — `Claim`, `Contradiction`, `ContextNote`, `AnalysisResult`, `ScrapedContent`, `PoliticianProfile` are all neutral.

```bash
cp "~/OppTracker/politracker/src/models.py" src/models.py
```

Then edit `src/models.py` — remove the `OppoBrief` class entirely (it references vulnerabilities, strongest_attacks, suggested_counters, narrative_frames — all campaign concepts).

- [ ] **Step 3: Copy and clean tools.py**

Copy `tools.py`, then remove:
- `store_oppo_brief()` function (campaign opposition briefs)
- `store_brief()` function (legacy brief storage)
- `get_oppo_brief_context()` function (campaign brief context)
- `export_dashboard()` function (politracker dashboard — we'll have generate.py instead)
- Any imports only used by removed functions

```bash
cp "~/OppTracker/politracker/src/tools.py" src/tools.py
```

Then edit to remove the above functions. Keep: `store_claim()`, `store_contradiction()`, `store_context_note()`, `store_analysis()`, `retrieve_context()`, `get_opponent_summary()`, `query_claims()`, `search_similar_claims()`, `get_contradictions()`, `get_context_notes()`.

- [ ] **Step 4: Fix import paths**

All source files reference `src.db`, `src.models`, etc. Since we're keeping the same `src/` structure, imports should work. Verify:

```bash
cd ~/atmina
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.db import get_db, init_db
from src.models import Claim, Contradiction, ContextNote
from src.topic_map import normalize_topic, get_all_group_names
from src.embeddings import chunk_text, embed_text
from src.analyze import get_pending_politicians
from src.tools import store_claim, store_contradiction
print('All imports OK')
print(f'Topics: {len(get_all_group_names())}')
"
```

Expected: "All imports OK" and "Topics: 26"

- [ ] **Step 5: Verify against live DB**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.db import get_db
from src.analyze import get_pending_politicians
db = get_db('data/atmina.db')
pending = get_pending_politicians(days=30)
print(f'Politicians with recent docs: {len(pending)}')
for p in pending[:5]:
    print(f'  {p[\"name\"]} ({p[\"party\"]}) — {p[\"doc_count\"]} docs')
"
```

- [ ] **Step 6: Commit**

```bash
git add src/db.py src/models.py src/topic_map.py src/embeddings.py src/analyze.py src/tools.py
git commit -m "feat: migrate core pipeline — db, models, topics, embeddings, analysis, tools"
```

---

## Task 4: Migrate Scraping Pipeline

Copy ingest.py, social.py, saeima.py. Fix social.py priority ordering to be neutral (alphabetical by party instead of MMN-first).

**Files:**
- Copy: `ingest.py` → `src/ingest.py` (as-is — already neutral)
- Copy: `social.py` → `src/social.py` (fix priority dict)
- Copy: `saeima.py` → `src/saeima.py` (as-is — schema fix already in DB)
- Copy: `x_scraper.py` → `src/x_scraper.py` (as-is if it exists)
- Copy: `x_mentions.py` → `src/x_mentions.py` (as-is if it exists)
- Copy: auth/credential helpers as needed

- [ ] **Step 1: Copy scraping files**

```bash
cd ~/atmina
cp "~/OppTracker/politracker/src/ingest.py" src/ingest.py
cp "~/OppTracker/politracker/src/social.py" src/social.py
cp "~/OppTracker/politracker/src/saeima.py" src/saeima.py
# Copy supporting files if they exist
cp "~/OppTracker/politracker/src/x_scraper.py" src/x_scraper.py 2>/dev/null
cp "~/OppTracker/politracker/src/x_mentions.py" src/x_mentions.py 2>/dev/null
cp "~/OppTracker/politracker/src/calibration.py" src/calibration.py 2>/dev/null
```

- [ ] **Step 2: Fix social.py priority ordering**

In `src/social.py`, find the `_FETCH_PRIORITY` dict and change it to neutral alphabetical ordering (no MMN-first bias):

Replace:
```python
_FETCH_PRIORITY = {
    "potential_ally": 1,    # MMN members first
    "opponent": 2,
    "coalition_partner": 3,
    "neutral": 4,
    "influencer": 5,
    "journalist": 6,
    "inactive": 9,
}
```

With:
```python
_FETCH_PRIORITY = {
    "opponent": 1,
    "coalition_partner": 1,
    "potential_ally": 1,
    "neutral": 2,
    "influencer": 3,
    "journalist": 3,
    "inactive": 9,
}
```

All active politicians are fetched with equal priority. Only inactive ones are deprioritized.

- [ ] **Step 3: Copy data files**

```bash
# X auth cookies (gitignored)
cp "~/OppTracker/politracker/data/x_cookies.json" data/x_cookies.json 2>/dev/null
# Saeima vote snapshots
cp "~/OppTracker/politracker/data/saeima_votes/"*.md data/saeima_votes/ 2>/dev/null
# Sources config if YAML-based
cp "~/OppTracker/politracker/sources.yaml" sources.yaml 2>/dev/null
cp "~/OppTracker/politracker/data/sources.yaml" data/sources.yaml 2>/dev/null
```

- [ ] **Step 4: Verify imports**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.ingest import ingest_all
from src.social import fetch_all_twitter
from src.saeima import init_saeima_tables, process_vote_snapshot
print('All scraping imports OK')
"
```

- [ ] **Step 5: Commit**

```bash
git add src/ingest.py src/social.py src/saeima.py src/x_scraper.py src/x_mentions.py src/calibration.py data/saeima_votes/ sources.yaml data/sources.yaml 2>/dev/null
git commit -m "feat: migrate scraping pipeline — ingest, social (neutral priority), saeima"
```

---

## Task 5: Wiki System (Redesigned)

Build the new frontmatter-only wiki sync. This is NEW code — not a copy of politracker's wiki.py.

**Files:**
- Create: `src/wiki.py`
- Create: `tests/test_wiki.py`

- [ ] **Step 1: Write wiki tests**

```python
# tests/test_wiki.py
import sqlite3
import tempfile
import pytest
from pathlib import Path


def _create_test_db(path):
    """Minimal DB for wiki testing."""
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, party TEXT, role TEXT, relationship_type TEXT DEFAULT 'neutral', name_forms TEXT DEFAULT '[]')")
    db.execute("CREATE TABLE claims (id INTEGER PRIMARY KEY, opponent_id INTEGER, topic TEXT, stance TEXT, confidence REAL, salience REAL, source_url TEXT, stated_at TEXT)")
    db.execute("CREATE TABLE contradictions (id INTEGER PRIMARY KEY, opponent_id INTEGER, claim_old_id INTEGER, claim_new_id INTEGER, topic TEXT, summary TEXT, severity TEXT, confirmed BOOLEAN DEFAULT 0, reviewed BOOLEAN DEFAULT 0, detected_at TEXT)")
    db.execute("CREATE TABLE saeima_individual_votes (id INTEGER PRIMARY KEY, vote_id INTEGER, deputy_name TEXT, faction TEXT, vote TEXT, politician_id INTEGER)")
    db.execute("INSERT INTO tracked_politicians (id, name, party, role) VALUES (1, 'Testa Politiķe', 'TP', 'Deputāte')")
    db.execute("INSERT INTO claims (opponent_id, topic, stance, confidence, salience, stated_at) VALUES (1, 'Budžets un finanses', 'Atbalsta nodokļu samazināšanu', 0.85, 0.7, '2026-04-01')")
    db.commit()
    return db


def test_wiki_sync_creates_index(tmp_path):
    from src.wiki import wiki_sync
    db_path = str(tmp_path / "test.db")
    _create_test_db(db_path)
    wiki_dir = tmp_path / "wiki"
    result = wiki_sync(db_path=db_path, wiki_dir=str(wiki_dir))
    assert (wiki_dir / "index.md").exists()
    assert result["persons"] >= 1


def test_wiki_sync_creates_person_stub(tmp_path):
    from src.wiki import wiki_sync
    db_path = str(tmp_path / "test.db")
    _create_test_db(db_path)
    wiki_dir = tmp_path / "wiki"
    wiki_sync(db_path=db_path, wiki_dir=str(wiki_dir))
    person_files = list((wiki_dir / "persons").glob("*.md"))
    assert len(person_files) >= 1
    content = person_files[0].read_text(encoding="utf-8")
    assert "---" in content  # Has frontmatter
    assert "name:" in content
    assert "party:" in content
    assert "claims:" in content


def test_wiki_sync_preserves_manual_content(tmp_path):
    from src.wiki import wiki_sync
    db_path = str(tmp_path / "test.db")
    _create_test_db(db_path)
    wiki_dir = tmp_path / "wiki"

    # First sync — creates stub
    wiki_sync(db_path=db_path, wiki_dir=str(wiki_dir))
    person_file = list((wiki_dir / "persons").glob("*.md"))[0]

    # Add manual content
    original = person_file.read_text(encoding="utf-8")
    person_file.write_text(original + "\n\n## Mans profils\n\nŠī ir manuāla piezīme.\n", encoding="utf-8")

    # Second sync — should preserve manual content
    wiki_sync(db_path=db_path, wiki_dir=str(wiki_dir))
    updated = person_file.read_text(encoding="utf-8")
    assert "Mans profils" in updated
    assert "manuāla piezīme" in updated


def test_index_groups_by_party(tmp_path):
    from src.wiki import wiki_sync
    db_path = str(tmp_path / "test.db")
    db = _create_test_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id, name, party, role) VALUES (2, 'Otrs Tests', 'JV', 'Deputāts')")
    db.commit()
    db.close()
    wiki_dir = tmp_path / "wiki"
    wiki_sync(db_path=db_path, wiki_dir=str(wiki_dir))
    index = (wiki_dir / "index.md").read_text(encoding="utf-8")
    assert "## JV" in index or "## Jaunā Vienotība" in index or "JV" in index
    # Should NOT contain relationship_type groupings
    assert "Opozīcija" not in index
    assert "MMN" not in index or "## MMN" not in index  # MMN only as a party, not as a group label
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ~/atmina
.venv/Scripts/python -m pytest tests/test_wiki.py -v
```

- [ ] **Step 3: Implement wiki.py**

```python
# src/wiki.py
"""Obsidian wiki sync — frontmatter-only updates, manual content preserved."""

import sqlite3
import re
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
_DEFAULT_WIKI = _PROJECT_ROOT / "wiki"
_DEFAULT_DB = _PROJECT_ROOT / "data" / "atmina.db"


def _slugify(name: str) -> str:
    table = str.maketrans("āčēģīķļņōŗšūž ĀČĒĢĪĶĻŅŌŖŠŪŽ", "acegiklnorsuz-acegiklnorsuz")
    slug = name.lower().translate(table)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    return slug.strip("-")


def _get_db(db_path: str) -> sqlite3.Connection:
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split markdown into (frontmatter_dict, body). Body is everything after closing ---."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    import yaml
    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2]
    return fm, body


def _render_frontmatter(data: dict) -> str:
    """Render YAML frontmatter block."""
    import yaml
    lines = ["---"]
    lines.append(yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False).rstrip())
    lines.append("---")
    return "\n".join(lines)


def _update_page(path: Path, new_frontmatter: dict):
    """Update frontmatter on existing page, preserving body. Create stub if new."""
    if path.exists():
        text = path.read_text(encoding="utf-8")
        _, body = _parse_frontmatter(text)
    else:
        body = "\n"  # Empty body for new stubs

    content = _render_frontmatter(new_frontmatter) + body
    path.write_text(content, encoding="utf-8")


def wiki_sync(db_path: str = None, wiki_dir: str = None) -> dict:
    """Sync wiki frontmatter from DB. Never modifies body content."""
    db_path = db_path or str(_DEFAULT_DB)
    wiki_dir = Path(wiki_dir) if wiki_dir else _DEFAULT_WIKI

    # Create directories
    for subdir in ["persons", "topics", "synthesis", "dailies"]:
        (wiki_dir / subdir).mkdir(parents=True, exist_ok=True)

    db = _get_db(db_path)

    # --- Person pages ---
    politicians = db.execute("""
        SELECT p.id, p.name, p.party, p.role,
            (SELECT COUNT(*) FROM claims WHERE opponent_id = p.id) AS claim_count,
            (SELECT COUNT(*) FROM contradictions WHERE opponent_id = p.id AND (confirmed=1 OR reviewed=0)) AS contradiction_count,
            (SELECT COUNT(*) FROM saeima_individual_votes WHERE politician_id = p.id) AS vote_count,
            (SELECT MAX(stated_at) FROM claims WHERE opponent_id = p.id) AS last_claim
        FROM tracked_politicians p
        WHERE p.relationship_type != 'inactive'
        ORDER BY p.name
    """).fetchall()

    # Get top topics per politician
    for p in politicians:
        top_topics = db.execute("""
            SELECT topic, COUNT(*) as cnt FROM claims
            WHERE opponent_id = ? GROUP BY topic ORDER BY cnt DESC LIMIT 5
        """, (p["id"],)).fetchall()
        topic_list = [t["topic"] for t in top_topics]

        fm = {
            "name": p["name"],
            "party": p["party"] or "",
            "role": p["role"] or "",
            "claims": p["claim_count"],
            "contradictions": p["contradiction_count"],
            "votes": p["vote_count"],
            "last_active": (p["last_claim"] or "")[:10],
            "topics": topic_list,
        }
        slug = _slugify(p["name"])
        _update_page(wiki_dir / "persons" / f"{slug}.md", fm)

    # --- Topic pages ---
    topics = db.execute("""
        SELECT topic, COUNT(*) as claim_count,
            COUNT(DISTINCT opponent_id) as politician_count,
            MAX(stated_at) as last_activity
        FROM claims
        GROUP BY topic
        ORDER BY claim_count DESC
    """).fetchall()

    topic_contradictions = {}
    for row in db.execute("SELECT topic, COUNT(*) as cnt FROM contradictions GROUP BY topic").fetchall():
        topic_contradictions[row["topic"]] = row["cnt"]

    for t in topics:
        top_pols = db.execute("""
            SELECT p.name, COUNT(*) as cnt FROM claims c
            JOIN tracked_politicians p ON c.opponent_id = p.id
            WHERE c.topic = ? GROUP BY p.name ORDER BY cnt DESC LIMIT 5
        """, (t["topic"],)).fetchall()

        fm = {
            "topic": t["topic"],
            "claims": t["claim_count"],
            "politicians": t["politician_count"],
            "contradictions": topic_contradictions.get(t["topic"], 0),
            "last_activity": (t["last_activity"] or "")[:10],
            "top_politicians": [p["name"] for p in top_pols],
        }
        slug = _slugify(t["topic"])
        _update_page(wiki_dir / "topics" / f"{slug}.md", fm)

    # --- Index ---
    # Group politicians by party
    by_party = {}
    for p in politicians:
        party = p["party"] or "Citi"
        by_party.setdefault(party, []).append(p)

    lines = [f"# atmina.lv — Wiki\n"]
    lines.append(f"Pēdējā sinhronizācija: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Sort parties by total claims descending
    party_order = sorted(by_party.keys(), key=lambda party: sum(p["claim_count"] for p in by_party[party]), reverse=True)

    for party in party_order:
        members = by_party[party]
        total_claims = sum(p["claim_count"] for p in members)
        lines.append(f"\n## {party} ({len(members)} politiķi, {total_claims} pozīcijas)\n")
        for p in sorted(members, key=lambda x: x["claim_count"], reverse=True):
            slug = _slugify(p["name"])
            lines.append(f"- [[{p['name']}]] — {p['claim_count']} pozīcijas, {p['contradiction_count']} pretrunas")

    lines.append(f"\n## Tēmas ({len(topics)})\n")
    for t in topics:
        slug = _slugify(t["topic"])
        lines.append(f"- [[{t['topic']}]] — {t['claim_count']} pozīcijas, {t['politician_count']} politiķi")

    # Scan synthesis pages
    synthesis_dir = wiki_dir / "synthesis"
    synthesis_pages = []
    for f in synthesis_dir.glob("*.md"):
        fm, _ = _parse_frontmatter(f.read_text(encoding="utf-8"))
        if fm.get("title"):
            synthesis_pages.append(fm)

    if synthesis_pages:
        lines.append(f"\n## Sintēzes ({len(synthesis_pages)})\n")
        for s in synthesis_pages:
            lines.append(f"- [[{s['title']}]]")

    (wiki_dir / "index.md").write_text("\n".join(lines), encoding="utf-8")

    # --- Log ---
    log_path = wiki_dir / "log.md"
    log_entry = f"- {datetime.now().strftime('%Y-%m-%d %H:%M')} — sync: {len(politicians)} persons, {len(topics)} topics\n"
    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8")
        log_path.write_text(existing + log_entry, encoding="utf-8")
    else:
        log_path.write_text("# Wiki Log\n\n" + log_entry, encoding="utf-8")

    db.close()

    return {"persons": len(politicians), "topics": len(topics), "synthesis": len(synthesis_pages)}
```

- [ ] **Step 4: Run tests**

```bash
.venv/Scripts/python -m pytest tests/test_wiki.py -v
```
Expected: All 4 tests PASS

- [ ] **Step 5: Run against real DB**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.wiki import wiki_sync
result = wiki_sync(db_path='data/atmina.db')
print(f'Synced: {result}')
"
```
Expected: 100+ persons, 20+ topics

- [ ] **Step 6: Commit**

```bash
git add src/wiki.py tests/test_wiki.py wiki/
git commit -m "feat: wiki system — frontmatter-only sync, grouped by party"
```

---

## Task 6: Static Site Generator + Templates + CSS

The big one. Creates `generate.py`, all Jinja2 templates, and the CSS design system.

**This task is large and should be dispatched to a sub-agent with the full spec context.**

**Files:**
- Create: `src/generate.py`
- Create: `assets/style.css`
- Create: All templates in `templates/`
- Copy: `chart.min.js` from politracker

**The sub-agent executing this task should:**

1. Read the spec at `docs/specs/2026-04-06-atmina-platform-design.md` (sections 5.1–5.4) for exact page specifications
2. Read the existing plan at `~\OppTracker\politracker\docs\superpowers\plans\2026-04-05-atmina-lv-launch.md` for detailed template code (Tasks 3-5 contain full HTML/CSS/Python)
3. Copy `chart.min.js` from politracker: `cp "~/OppTracker/politracker/templates/chart.min.js" assets/chart.min.js`

**Key implementation details:**

- `generate.py` queries `data/atmina.db` directly (read-only)
- Reads wiki person/topic pages for editorial content (body below frontmatter)
- Generates all HTML to `output/atmina/` and `output/agents/`
- All data embedded as JSON in pages — client-side JS filtering
- Dark theme, responsive, no framework
- Every page has OG meta tags
- Blog posts get individual pages at `output/atmina/blog/{date}.html`
- Politician pages at `output/atmina/politiki/{slug}.html`
- Assets copied to `output/atmina/assets/`

**Pages to generate:**
1. `index.html` — stats, top contradictions, recent votes, CTA
2. `pretrunas.html` — all contradictions, filterable by party/severity/topic
3. `pozicijas.html` — all claims, filterable table
4. `balsojumi.html` — votes with faction breakdowns
5. `tendences.html` — Chart.js charts (topics, politicians, timeline)
6. `analizes.html` — analysis hub linking to deep pieces
7. `deklaracijas.html` — party financing from content/analizes/
8. `blog.html` — blog index
9. `blog/{date}.html` — individual posts
10. `politiki/{slug}.html` — per-politician pages
11. `about.html` — methodology + ideology
12. `agents/index.html` — agents.atmina.lv landing page

**Test:** After generation, verify all HTML files exist and contain expected content:

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.generate import generate_public_site
result = generate_public_site()
print(result)
"
# Then:
ls output/atmina/*.html
ls output/atmina/politiki/ | head -10
ls output/agents/
```

- [ ] **Step 1: Copy chart.min.js**

```bash
cp "~/OppTracker/politracker/templates/chart.min.js" assets/chart.min.js
```

- [ ] **Step 2: Create assets/style.css**

Use the CSS from the previous plan (Task 3, Step 2) — dark theme design system with nav, cards, grids, filters, tables, stats, badges, hero, CTA, footer. Blue accent (`#3b82f6`), not indigo.

- [ ] **Step 3: Create all Jinja2 templates**

Create each template in `templates/`. Reference the detailed HTML from the previous plan (Tasks 3-4) for the full template code. Key templates: `base.html.j2`, `index.html.j2`, `pretrunas.html.j2`, `pozicijas.html.j2`, `balsojumi.html.j2`, `tendences.html.j2`, `analizes.html.j2`, `blog.html.j2`, `blog-post.html.j2`, `politician.html.j2`, `about.html.j2`, `agents.html.j2`.

- [ ] **Step 4: Create src/generate.py**

Reference the `generate_public_site()` implementation from the previous plan (Task 5, Step 3). Key additions:
- Read wiki person page bodies for politician profiles
- Read `content/analizes/*.md` for analysis pages
- Read `context_notes` (daily_brief/weekly_brief) for blog posts — but these are empty after migration, so blog starts fresh
- Generate agents.atmina.lv landing page

- [ ] **Step 5: Test generation**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -m src.generate
ls -la output/atmina/
ls -la output/atmina/politiki/ | wc -l
ls -la output/agents/
```

- [ ] **Step 6: Open in browser and verify**

```bash
start output/atmina/index.html
```

Check: stats render, contradictions show, nav works, politician links work, about page renders.

- [ ] **Step 7: Commit**

```bash
git add src/generate.py assets/ templates/ output/
git commit -m "feat: static site generator — all pages, dark theme, Chart.js"
```

---

## Task 7: Neutral Brief Generator + Routine

Create the neutral daily brief generator and simplified routine checker.

**Files:**
- Create: `src/briefs.py`
- Copy + modify: `src/routine.py`

- [ ] **Step 1: Create src/briefs.py**

```python
# src/briefs.py
"""Neutral daily/weekly brief generator for atmina.lv blog."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "data" / "atmina.db"


def generate_daily_brief(db_path: str = None, date: str = None) -> str:
    """Generate a neutral daily brief in markdown. No campaign framing."""
    db_path = db_path or str(_DB_PATH)
    date = date or datetime.now().strftime("%Y-%m-%d")
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    # Stats for the day
    doc_count = db.execute(
        "SELECT COUNT(*) FROM documents WHERE date(scraped_at) = ?", (date,)
    ).fetchone()[0]
    web_count = db.execute(
        "SELECT COUNT(*) FROM documents WHERE date(scraped_at) = ? AND platform = 'web'", (date,)
    ).fetchone()[0]
    x_count = doc_count - web_count

    claim_count = db.execute(
        "SELECT COUNT(*) FROM claims WHERE date(stated_at) = ?", (date,)
    ).fetchone()[0]
    contradiction_count = db.execute(
        "SELECT COUNT(*) FROM contradictions WHERE date(detected_at) = ?", (date,)
    ).fetchone()[0]

    # Active politicians
    active = db.execute("""
        SELECT p.name, p.party, COUNT(*) as cnt,
            GROUP_CONCAT(DISTINCT c.topic) as topics
        FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        WHERE date(c.stated_at) = ?
        GROUP BY p.id ORDER BY cnt DESC LIMIT 12
    """, (date,)).fetchall()

    # Claims by topic
    by_topic = db.execute("""
        SELECT topic, COUNT(*) as cnt FROM claims
        WHERE date(stated_at) = ? GROUP BY topic ORDER BY cnt DESC LIMIT 5
    """, (date,)).fetchall()

    # Build markdown
    lines = [f"# Dienas analīze — {date}\n"]

    lines.append("## Galvenais\n")
    lines.append(f"- **{doc_count} dokumenti** ({web_count} web + {x_count} Twitter/X), "
                 f"**{claim_count} jaunas pozīcijas**, **{contradiction_count} pretrunas**")

    if active:
        lines.append("\n## Aktīvākie politiķi\n")
        lines.append("| Politiķis | Partija | Pozīcijas | Galvenās tēmas |")
        lines.append("|-----------|---------|-----------|----------------|")
        for a in active:
            topics = (a["topics"] or "").replace(",", ", ")[:60]
            lines.append(f"| {a['name']} | {a['party'] or ''} | {a['cnt']} | {topics} |")

    if by_topic:
        lines.append("\n## Galvenās tēmas\n")
        for t in by_topic:
            lines.append(f"### {t['topic']} ({t['cnt']} pozīcijas)\n")
            # Get sample claims for this topic today
            samples = db.execute("""
                SELECT p.name, c.stance FROM claims c
                JOIN tracked_politicians p ON c.opponent_id = p.id
                WHERE date(c.stated_at) = ? AND c.topic = ?
                LIMIT 3
            """, (date, t["topic"])).fetchall()
            for s in samples:
                lines.append(f"- **{s['name']}:** {s['stance']}")
            lines.append("")

    db.close()
    return "\n".join(lines)
```

- [ ] **Step 2: Create simplified routine.py**

Copy from politracker and simplify — remove campaign-specific steps (reply strategy, oppo briefs, campaign-framed routine steps).

```bash
cp "~/OppTracker/politracker/src/routine.py" src/routine.py
```

Then edit `src/routine.py`:
- Remove steps: `reply_classification`, `briefs` (oppo briefs), `mentions` (MMN mentions)
- Keep steps: `ingest`, `analysis`, `contradictions`, `tensions`, `context_notes`, `daily_brief`, `wiki_sync`, `generate`
- Update labels to neutral Latvian

- [ ] **Step 3: Commit**

```bash
git add src/briefs.py src/routine.py
git commit -m "feat: neutral brief generator + simplified daily routine"
```

---

## Task 8: Content

Create the ideology document, adapt deklarāciju analysis, write CLAUDE.md.

**Files:**
- Create: `content/ideology.md`
- Create: `content/analizes/deklaracijas-2026.md`
- Create: `CLAUDE.md`

- [ ] **Step 1: Create ideology document**

Write `content/ideology.md` — the public ideology document from the spec (Section 10.1). Contains: what we believe, our principles (public data, verifiable sources, transparent methodology, declared perspective), system focus, how we make money.

- [ ] **Step 2: Adapt deklarāciju analysis**

Copy and adapt `~\OppTracker\Deklaracijas\ATSKAITE.md` to `content/analizes/deklaracijas-2026.md`. Add YAML frontmatter:

```yaml
---
title: "Partiju finansēšana 2025–2026"
description: "3,179 ziedojumi, 47 partijas, EUR 2.35M — kas finansē Latvijas politiku?"
date: "2026-04-02"
tags: ["KNAB", "ziedojumi", "partiju finanses"]
url: "deklaracijas.html"
---
```

Then paste the full ATSKAITE.md content below.

- [ ] **Step 3: Write CLAUDE.md**

Create `CLAUDE.md` for the atmina project — neutral project instructions. This should cover:
- Project overview (atmina.lv political transparency platform)
- Daily routine steps (neutral, no campaign framing)
- Critical rules (same Pydantic types, mandatory contradiction check, source_url required, etc.)
- Commands (venv activation, routine check, generate site, wiki sync)
- Tech stack
- Topic map (26 canonical groups)
- Wiki context (read wiki/index.md at session start)
- Timezone (Latvia UTC+3)
- UI language (Latvian)

Base it on the politracker CLAUDE.md but strip ALL MMN-specific content: campaign_voice references, party_ideology references, @brief-writer agent, @reply-strategist agent, reply strategy steps, oppo brief format, coalition map.

- [ ] **Step 4: Commit**

```bash
git add content/ CLAUDE.md
git commit -m "feat: content — ideology, deklarācijas analysis, project instructions"
```

---

## Task 9: Integration Test + Final Verification

Run the full pipeline end-to-end. Verify everything works together.

- [ ] **Step 1: Verify all imports**

```bash
cd ~/atmina
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.db import get_db, init_db
from src.models import Claim, Contradiction, ContextNote
from src.topic_map import normalize_topic, get_all_group_names
from src.embeddings import chunk_text
from src.analyze import get_pending_politicians, get_politician_documents, get_existing_claims, save_analysis
from src.tools import store_claim, store_contradiction, store_context_note
from src.ingest import ingest_all
from src.social import fetch_all_twitter
from src.saeima import init_saeima_tables
from src.wiki import wiki_sync
from src.generate import generate_public_site
from src.briefs import generate_daily_brief
from src.routine import print_routine
print('ALL IMPORTS OK')
"
```

- [ ] **Step 2: Verify DB integrity**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.db import get_db
db = get_db('data/atmina.db')
tables = [r[0] for r in db.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]
print(f'Tables: {len(tables)}')
for t in sorted(tables):
    count = db.execute(f'SELECT COUNT(*) FROM [{t}]').fetchone()[0]
    print(f'  {t}: {count} rows')
"
```

Expected: 100+ politicians, 900+ documents, 230+ claims, 21 contradictions, 18+ votes, 0 oppo_briefs, 0 mention_classifications.

- [ ] **Step 3: Run wiki sync**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.wiki import wiki_sync
result = wiki_sync(db_path='data/atmina.db')
print(f'Wiki synced: {result}')
"
```

Verify: 100+ person files in wiki/persons/, 20+ topic files, index.md grouped by party.

- [ ] **Step 4: Generate the public site**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -m src.generate
```

Verify:
```bash
ls output/atmina/*.html | wc -l     # Should be 8+ HTML files
ls output/atmina/politiki/ | wc -l  # Should be 100+ politician pages
ls output/agents/                    # Should have index.html
```

- [ ] **Step 5: Open and visually verify**

```bash
start output/atmina/index.html
```

Check:
- Stats render correctly (politicians, claims, contradictions, votes)
- Contradiction cards show with source links
- Nav links work (pretrunas, pozicijas, balsojumi, tendences, analizes, blog, about)
- Politician pages load and show claims/contradictions
- About page shows ideology
- Analīzes page links to deklarācijas
- agents.atmina.lv landing page renders

- [ ] **Step 6: Run type check**

```bash
cd ~/atmina
.venv/Scripts/python -m py_compile src/db.py
.venv/Scripts/python -m py_compile src/models.py
.venv/Scripts/python -m py_compile src/generate.py
.venv/Scripts/python -m py_compile src/wiki.py
.venv/Scripts/python -m py_compile src/briefs.py
echo "All files compile OK"
```

- [ ] **Step 7: Push to GitHub**

```bash
cd ~/atmina
# Create GitHub repo first if not done
git add -A
git commit -m "feat: atmina v1 — complete platform with public site generator"
git remote add origin https://github.com/imaksligais/atmina.git
git push -u origin master
```

---

## Summary: Execution Order

| Task | What | Depends On | Parallelizable |
|------|------|-----------|----------------|
| **1. Scaffolding** | Project structure, venv, deps | Nothing | First |
| **2. DB Migration** | Copy + clean DB, add deputies | Task 1 | After 1 |
| **3. Core Pipeline** | db.py, models, topics, analyze, tools | Task 1 | With 4 |
| **4. Scraping** | ingest, social, saeima | Task 1 | With 3 |
| **5. Wiki** | New wiki.py with frontmatter sync | Tasks 2, 3 | With 6 |
| **6. Static Site** | generate.py, templates, CSS | Tasks 2, 3 | With 5 |
| **7. Briefs + Routine** | briefs.py, routine.py | Tasks 3, 4 | With 5, 6 |
| **8. Content** | ideology, deklarācijas, CLAUDE.md | Task 1 | With anything |
| **9. Integration Test** | Full pipeline verification | All above | Last |

**Parallel dispatch strategy:**
- Round 1: Task 1 (scaffolding)
- Round 2: Tasks 2 + 8 (DB migration + content — independent)
- Round 3: Tasks 3 + 4 (core pipeline + scraping — independent)
- Round 4: Tasks 5 + 6 + 7 (wiki + generator + briefs — can partially parallelize)
- Round 5: Task 9 (integration test — after everything)
