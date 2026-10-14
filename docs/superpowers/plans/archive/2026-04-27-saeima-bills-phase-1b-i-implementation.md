# Saeima Bills Phase 1B-i Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Atver `saeima_bills` DB publikai — pievieno detail page `/likumprojekti/<slug>.html` (91+ failu), bills-list 3. subtab uz `/balsojumi.html`, vote-card iekšējo cross-link, un izlabo P14 motif regex gap.

**Architecture:** Server-rendered Jinja2 (kā `balsojumi.html`, NE JSON-split kā `pozicijas.html` — 91 bills ir mazs). Datu fetcheri SELECT'ē no esošās Phase 1A schema. Detail lapa `output/atmina/likumprojekti/` ar `assets_prefix="../"`. Iekšēji cross-linki balsojumi → likumprojekti. CSS atkārto esošās `.vote-card` paterna konvencijas.

**Tech Stack:** Python 3.11+ · SQLite (WAL) · Pydantic v2 · Jinja2 · pytest · BeautifulSoup4 (esošs).

**Spec atsauce:** [`docs/superpowers/specs/2026-04-27-saeima-bills-phase-1b-i-design.md`](../specs/2026-04-27-saeima-bills-phase-1b-i-design.md)

---

## Task 0: Worktree setup un P14 motif gap fix

**Files:**
- Setup: jauns git worktree `.worktrees/saeima-bills-phase-1b-i` uz branch `saeima-bills-phase-1b-i`
- Modify: `src/saeima.py` — `_DOCUMENT_NR_RE` regex
- Test: `tests/test_saeima_bills.py` — pievieno unparenthesized P14 testu
- Run: `scripts/backfill_saeima_bills.py` (idempotents)

- [ ] **Step 1: Izveido worktree**

```bash
git worktree add .worktrees/saeima-bills-phase-1b-i -b saeima-bills-phase-1b-i master
cd .worktrees/saeima-bills-phase-1b-i
```

Verificē, ka esi jaunā branch'ā: `git status` rāda `On branch saeima-bills-phase-1b-i` un clean working tree.

- [ ] **Step 2: Aktivizē venv un palaiž esošos testus, lai apstiprinātu zaļu baseline**

```bash
source ../../.venv/Scripts/activate
python -m pytest tests/test_saeima_bills.py tests/test_saeima_bills_integration.py -q
```

Sagaidāms: 57 passed (per HANDOFF). Ja ne, STOP un izpētī, kāpēc baseline nesakrīt.

- [ ] **Step 3: Atrod un nolasi pašreizējo `_DOCUMENT_NR_RE`**

Atver `src/saeima.py` un atrod `_DOCUMENT_NR_RE` definīciju (grep: `_DOCUMENT_NR_RE = re.compile`). Apstiprini, ka regex prasa parentheses (kaut kas līdzīgs `r"\((\d+)/(Lp14|Lm14|P14)\)"`).

- [ ] **Step 4: Pievieno failing testu unparenthesized P14**

Atver `tests/test_saeima_bills.py` un pievieno klasē `TestResolveBillFromMotif` (vai līdzīgā):

```python
def test_resolve_bill_from_motif_unparenthesized_p14():
    """P14 motif bez paēzēm joprojām jāatpazīst (ievada 2026-04-27 fix)."""
    motif = "Par paziņojumu par dronu uzbrukumiem 127/P14"
    assert resolve_bill_from_motif(motif) == "127/P14"

def test_resolve_bill_from_motif_parenthesized_still_works():
    """Esošā parenthesized forma nesalūst pēc regex paplašināšanas."""
    motif = "Grozījumi Imigrācijas likumā (1315/Lp14)"
    assert resolve_bill_from_motif(motif) == "1315/Lp14"
```

- [ ] **Step 5: Palaiž testus un apstiprini, ka jaunais fail-ē**

```bash
python -m pytest tests/test_saeima_bills.py::TestResolveBillFromMotif::test_resolve_bill_from_motif_unparenthesized_p14 -v
```

Sagaidāms: FAIL ar `AssertionError` (regex neatpazīst).

- [ ] **Step 6: Paplašini regex `_DOCUMENT_NR_RE`**

`src/saeima.py` aizvieto:
```python
_DOCUMENT_NR_RE = re.compile(r"\(?(\d+)\s*/\s*(Lp14|Lm14|P14)\)?")
```

(Optional parens — match arī ar/bez paēzēm; whitespace tolerance ap `/`.)

- [ ] **Step 7: Verificē, ka jaunie un esošie testi visi paiet**

```bash
python -m pytest tests/test_saeima_bills.py tests/test_saeima_bills_integration.py -q
```

Sagaidāms: 59 passed (57 + 2 jauni). Ja kāds esošs fail-ē, regex pārāk plašs — sašaurini un atkārto.

- [ ] **Step 8: Re-run backfill, verificē P14 bills tiek izveidoti**

```bash
python scripts/backfill_saeima_bills.py
PYTHONIOENCODING=utf-8 python -c "
import sqlite3
db = sqlite3.connect('data/atmina.db')
print('Bills:', db.execute(\"SELECT COUNT(*) FROM saeima_bills\").fetchone()[0])
print('P14 bills:', db.execute(\"SELECT COUNT(*) FROM saeima_bills WHERE bill_type='P14'\").fetchone()[0])
print('Stages:', db.execute(\"SELECT COUNT(*) FROM saeima_bill_stages\").fetchone()[0])
"
```

Sagaidāms: P14 bills ≥ 1 (precīzs skaits ir 1-5 atkarīgs no unique `document_nr` 5 P14 balsojumos). Bills total = 91 + N (kur N = jaunie P14). Ja P14 = 0, regex joprojām negaida tos motif'us — izdrukā motif paraugu un pielāgo regex.

- [ ] **Step 9: Audit guardrail**

```bash
python scripts/audit_saeima_vote_results.py
```

Sagaidāms: 0 errors. Ja audit fail-ē, STOP un izpētī.

- [ ] **Step 10: Commit**

```bash
git add src/saeima.py tests/test_saeima_bills.py
git commit -m "$(cat <<'EOF'
fix(saeima): _DOCUMENT_NR_RE — accept unparenthesized P14 motifs

Phase 1A backfill izveidoja 0 P14 bills, lai gan DB ir 5 P14
balsojumi — regex prasīja parens, bet daļa motif'u nāk bez tām.
Paplašina pattern uz \(?...\)? ar whitespace tolerance.

Phase 1B-i HANDOFF Phase 0.7 punkts #6.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 1: Datu fetcheri (`_fetch_bills`, `_fetch_bill_detail`, `_fetch_votes` patch)

**Files:**
- Modify: `src/generate.py` — pievieno `_fetch_bills`, `_fetch_bill_detail`; pielāgo `_fetch_votes`
- Test: `tests/test_generate_bills.py` (jauns fails)

- [ ] **Step 1: Izveido jaunu testa failu ar fixture**

`tests/test_generate_bills.py`:

```python
"""Phase 1B-i — _fetch_bills, _fetch_bill_detail, _generate_bill_pages."""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.db import init_db, get_db
from src.saeima import init_saeima_bills, init_saeima_tables, upsert_bill, append_bill_stage


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def db_with_bills(tmp_path):
    """SQLite ar 2 Lp14 + 1 Lm14 + 1 P14 fixture bills, kuriem ir stages."""
    fd, path = tempfile.mkstemp(suffix=".db", dir=str(tmp_path))
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    db = get_db(path)
    # Bill 1: Lp14, full lifecycle (4 stages)
    bid1 = upsert_bill(db, "1315/Lp14", "Grozījumi Aizsardzības likumā", "Lp14",
                       institutional_submitter="Ministru kabinets", topic="Aizsardzība un drošība")
    append_bill_stage(db, bid1, "iesniegts", None, "2026-02-10")
    append_bill_stage(db, bid1, "1.lasījums", "pieņemts", "2026-03-05")
    append_bill_stage(db, bid1, "2.lasījums", "pieņemts", "2026-04-01")
    append_bill_stage(db, bid1, "3.lasījums", "pieņemts", "2026-04-23")
    # Bill 2: Lp14, only 2 stages (jaunāks)
    bid2 = upsert_bill(db, "1098/Lp14", "Iepirkumu vienkāršošana", "Lp14",
                       topic="Valsts pārvalde")
    append_bill_stage(db, bid2, "iesniegts", None, "2026-04-15")
    append_bill_stage(db, bid2, "1.lasījums", "noraidīts", "2026-04-25")
    # Bill 3: Lm14
    bid3 = upsert_bill(db, "952/Lm14", "Tiesneša iecelšana — Anna Bērziņa", "Lm14")
    append_bill_stage(db, bid3, "tiesneša_amats", "pieņemts", "2026-04-20")
    # Bill 4: P14 — paziņojums
    bid4 = upsert_bill(db, "127/P14", "Paziņojums par dronu uzbrukumiem", "P14")
    append_bill_stage(db, bid4, "iesniegts", None, "2026-04-22")
    append_bill_stage(db, bid4, "paziņojuma_balsojums", "pieņemts", "2026-04-25")
    db.commit()
    db.close()
    yield path
    _safe_unlink(path)
```

- [ ] **Step 2: Pievieno failing testu `test_fetch_bills_shape`**

```python
def test_fetch_bills_shape(db_with_bills):
    from src.generate import _fetch_bills
    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    db.close()
    assert len(bills) == 3
    b1 = next(b for b in bills if b["document_nr"] == "1315/Lp14")
    assert b1["slug"] == "1315-lp14"
    assert b1["bill_type"] == "Lp14"
    assert b1["title"] == "Grozījumi Aizsardzības likumā"
    assert b1["topic"] == "Aizsardzība un drošība"
    assert b1["current_stage"] == "3.lasījums"
    assert b1["current_status"] == "pieņemts"
    assert b1["stage_count"] == 4
    assert b1["institutional_submitter"] == "Ministru kabinets"
    assert b1["submitter_count"] == 0  # nekāda junction rinda fixture'ā
```

- [ ] **Step 3: Palaiž, apstiprini FAIL**

```bash
python -m pytest tests/test_generate_bills.py::test_fetch_bills_shape -v
```

Sagaidāms: FAIL ar `ImportError: cannot import name '_fetch_bills'`.

- [ ] **Step 4: Implementē `_fetch_bills` `src/generate.py`**

Pievieno aiz pēdējā `_fetch_*` funkcijas (piem. aiz `_fetch_blog_posts` ~līnija 2322):

```python
def _bill_slug(document_nr: str) -> str:
    """'1315/Lp14' -> '1315-lp14'."""
    return document_nr.lower().replace("/", "-")


def _fetch_bills(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Fetch all bills with denormalized current_stage/status + counts.

    Returns list ordered by last_updated_at DESC (newest first).
    Used both for /balsojumi.html#bills-list grid and as index for detail page generation.
    """
    rows = db.execute("""
        SELECT
            b.id, b.document_nr, b.bill_type, b.title, b.summary, b.topic,
            b.current_stage, b.current_status,
            b.first_seen_at, b.last_updated_at,
            b.institutional_submitter,
            (SELECT COUNT(*) FROM saeima_bill_politicians WHERE bill_id=b.id AND role='submitter') AS submitter_count,
            (SELECT COUNT(*) FROM saeima_bill_stages WHERE bill_id=b.id) AS stage_count,
            (SELECT COUNT(*) FROM saeima_votes WHERE bill_id=b.id) AS vote_count
        FROM saeima_bills b
        ORDER BY b.last_updated_at DESC, b.id DESC
    """).fetchall()
    return [
        {
            "id": r["id"],
            "document_nr": r["document_nr"],
            "slug": _bill_slug(r["document_nr"]),
            "bill_type": r["bill_type"],
            "title": r["title"],
            "summary": r["summary"],
            "topic": r["topic"],
            "current_stage": r["current_stage"],
            "current_status": r["current_status"],
            "first_seen_at": r["first_seen_at"],
            "last_updated_at": r["last_updated_at"],
            "institutional_submitter": r["institutional_submitter"],
            "submitter_count": r["submitter_count"],
            "stage_count": r["stage_count"],
            "vote_count": r["vote_count"],
        }
        for r in rows
    ]
```

- [ ] **Step 5: Palaiž, apstiprini PASS**

```bash
python -m pytest tests/test_generate_bills.py::test_fetch_bills_shape -v
```

Sagaidāms: PASS.

- [ ] **Step 6: Pievieno sort testu**

```python
def test_fetch_bills_sort_by_last_updated_desc(db_with_bills):
    from src.generate import _fetch_bills
    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    db.close()
    timestamps = [b["last_updated_at"] for b in bills]
    assert timestamps == sorted(timestamps, reverse=True), \
        f"Bills must be ordered newest-first; got {timestamps}"
```

Run: `python -m pytest tests/test_generate_bills.py::test_fetch_bills_sort_by_last_updated_desc -v` → PASS.

- [ ] **Step 7: Pievieno failing `test_fetch_bill_detail_full_lp14`**

```python
def test_fetch_bill_detail_full_lp14(db_with_bills):
    from src.generate import _fetch_bills, _fetch_bill_detail
    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    bid = next(b["id"] for b in bills if b["document_nr"] == "1315/Lp14")
    detail = _fetch_bill_detail(db, bid)
    db.close()
    assert detail["document_nr"] == "1315/Lp14"
    assert detail["slug"] == "1315-lp14"
    assert len(detail["stages"]) == 4
    assert detail["stages"][0]["stage_name"] == "iesniegts"
    assert detail["stages"][-1]["stage_name"] == "3.lasījums"
    assert detail["stages"][-1]["stage_result"] == "pieņemts"
    assert detail["submitters_individual"] == []  # fixture'ā nav junction
    assert detail["amendment_authors"] == []
    assert detail["external_document_url"] is None
```

Run → FAIL ar `ImportError`.

- [ ] **Step 8: Implementē `_fetch_bill_detail`**

```python
def _fetch_bill_detail(db: sqlite3.Connection, bill_id: int) -> Optional[dict[str, Any]]:
    """Fetch one bill ar pilnu stages timeline + submitters + amendment_authors.

    Returns None ja bill_id neeksistē. Stages ordered chronologiski (stage_date ASC, id ASC).
    """
    bill_row = db.execute("""
        SELECT b.id, b.document_nr, b.bill_type, b.title, b.summary, b.topic,
               b.current_stage, b.current_status,
               b.first_seen_at, b.last_updated_at, b.institutional_submitter
        FROM saeima_bills b WHERE b.id=?
    """, (bill_id,)).fetchone()
    if bill_row is None:
        return None

    # Stages ar joined balsojuma summary
    stages = []
    for s in db.execute("""
        SELECT
            st.id, st.stage_name, st.stage_result, st.stage_date, st.amendment_nr, st.vote_id,
            v.summary AS vote_summary, v.total_par, v.total_pret, v.total_atturas
        FROM saeima_bill_stages st
        LEFT JOIN saeima_votes v ON v.id = st.vote_id
        WHERE st.bill_id=? ORDER BY st.stage_date ASC, st.id ASC
    """, (bill_id,)).fetchall():
        stages.append({
            "stage_name": s["stage_name"],
            "stage_result": s["stage_result"],
            "stage_date": s["stage_date"],
            "amendment_nr": s["amendment_nr"],
            "vote_id": s["vote_id"],
            "vote_summary": s["vote_summary"],
            "total_par": s["total_par"],
            "total_pret": s["total_pret"],
            "total_atturas": s["total_atturas"],
            # faction_breakdown aizpildīts vēlākā Step (atsevišķs join)
        })

    # Submitters (junction WHERE role='submitter')
    submitters = []
    for s in db.execute("""
        SELECT tp.slug, tp.name, tp.party
        FROM saeima_bill_politicians j
        JOIN tracked_politicians tp ON tp.id = j.politician_id
        WHERE j.bill_id=? AND j.role='submitter'
        ORDER BY tp.name ASC
    """, (bill_id,)).fetchall():
        submitters.append({"slug": s["slug"], "name": s["name"], "party": s["party"]})

    # External document URL — paņem no jebkura saistītā balsojuma
    ext = db.execute("""
        SELECT v.document_url FROM saeima_votes v
        WHERE v.bill_id=? AND v.document_url IS NOT NULL
        ORDER BY v.id DESC LIMIT 1
    """, (bill_id,)).fetchone()

    return {
        "id": bill_row["id"],
        "document_nr": bill_row["document_nr"],
        "slug": _bill_slug(bill_row["document_nr"]),
        "bill_type": bill_row["bill_type"],
        "title": bill_row["title"],
        "summary": bill_row["summary"],
        "topic": bill_row["topic"],
        "current_stage": bill_row["current_stage"],
        "current_status": bill_row["current_status"],
        "first_seen_at": bill_row["first_seen_at"],
        "last_updated_at": bill_row["last_updated_at"],
        "institutional_submitter": bill_row["institutional_submitter"],
        "stages": stages,
        "submitters_individual": submitters,
        "amendment_authors": [],
        "external_document_url": ext["document_url"] if ext else None,
    }
```

- [ ] **Step 9: Run un PASS**

```bash
python -m pytest tests/test_generate_bills.py::test_fetch_bill_detail_full_lp14 -v
```

Sagaidāms: PASS.

- [ ] **Step 10: Edge case testi**

```python
def test_fetch_bill_detail_handles_missing_summary(db_with_bills):
    from src.generate import _fetch_bills, _fetch_bill_detail
    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    bid = next(b["id"] for b in bills if b["document_nr"] == "1098/Lp14")
    detail = _fetch_bill_detail(db, bid)
    db.close()
    assert detail["summary"] is None
    assert len(detail["stages"]) == 2

def test_fetch_bill_detail_returns_none_for_missing_id(db_with_bills):
    from src.generate import _fetch_bill_detail
    db = get_db(db_with_bills)
    detail = _fetch_bill_detail(db, 99999)
    db.close()
    assert detail is None
```

Run → PASS.

- [ ] **Step 11: Patch `_fetch_votes` lai pievienotu `bill_id` un `bill_slug`**

`src/generate.py::_fetch_votes` (ap līniju 1031). Atrod SQL SELECT'u un pievieno LEFT JOIN:

Pirms — esošais query (paraugs):
```python
rows = db.execute("""
    SELECT v.id, v.motif, v.vote_date, v.result, v.summary,
           v.document_url, v.document_nr, v.topic, ...
    FROM saeima_votes v
    ...
""")
```

Pēc:
```python
rows = db.execute("""
    SELECT v.id, v.motif, v.vote_date, v.result, v.summary,
           v.document_url, v.document_nr, v.topic, ...,
           v.bill_id,
           b.document_nr AS bill_doc_nr
    FROM saeima_votes v
    LEFT JOIN saeima_bills b ON b.id = v.bill_id
    ...
""")
```

Un dict outputs pievieno:
```python
{
    ...,
    "bill_id": r["bill_id"],
    "bill_slug": _bill_slug(r["bill_doc_nr"]) if r["bill_doc_nr"] else None,
}
```

- [ ] **Step 12: Pievieno `_fetch_votes` patch testu**

Šis ir integrācijas tests — fixtured DB ar bill un vote, kas saistīts ar bill:

```python
def test_fetch_votes_includes_bill_slug_when_linked(db_with_bills, tmp_path):
    """_fetch_votes patch — votes ar bill_id iegūst bill_slug; bez bill_id → None."""
    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    bid = next(b["id"] for b in bills if b["document_nr"] == "1315/Lp14")
    # Insert one vote linked to bill
    db.execute("""
        INSERT INTO saeima_votes (motif, vote_date, result, document_nr, bill_id)
        VALUES (?, ?, ?, ?, ?)
    """, ("Test motif (1315/Lp14)", "2026-03-05", "Pieņemts", "1315/Lp14", bid))
    # And one without bill_id
    db.execute("""
        INSERT INTO saeima_votes (motif, vote_date, result, document_nr)
        VALUES (?, ?, ?, ?)
    """, ("Procedurāls", "2026-04-01", "Pieņemts", None))
    db.commit()
    db.close()

    from src.generate import _fetch_votes
    db = get_db(db_with_bills)
    votes = _fetch_votes(db)
    db.close()
    linked = next(v for v in votes if v["motif"] == "Test motif (1315/Lp14)")
    proc = next(v for v in votes if v["motif"] == "Procedurāls")
    assert linked["bill_slug"] == "1315-lp14"
    assert proc["bill_slug"] is None
```

Pievieno `_fetch_bills` import augšā: `from src.generate import _fetch_bills`.

Run → ja FAIL, korigē patch'u; PASS, ej tālāk.

- [ ] **Step 13: Apstiprini, ka esošie generate testi nav saplīsuši**

```bash
python -m pytest tests/test_generate.py -q
```

Sagaidāms: tādu pat skaits passing kā pirms patch'a (vai vairāk, ja jaunie testi).

- [ ] **Step 14: Commit**

```bash
git add src/generate.py tests/test_generate_bills.py
git commit -m "$(cat <<'EOF'
feat(generate): _fetch_bills + _fetch_bill_detail + _fetch_votes bill_slug

Phase 1B-i datu slānis. _fetch_bills atgriež visus bills ar
denormalizētiem stage/status counts grid renderēšanai;
_fetch_bill_detail atgriež pilnu stages timeline + submitters
detail lapai. _fetch_votes patch pievieno bill_slug joined no
saeima_bills, lai vote-card var renderēt iekšējo cross-link.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Detail template `templates/likumprojekts.html.j2`

**Files:**
- Create: `templates/likumprojekts.html.j2`
- Test: `tests/test_generate_bills.py` — pievieno render testus

- [ ] **Step 1: Pievieno failing render testu**

```python
def test_likumprojekts_template_renders_lp14(db_with_bills):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _fetch_bill_detail, _safe_url_filter

    db = get_db(db_with_bills)
    bid = next(b["id"] for b in _fetch_bills(db) if b["document_nr"] == "1315/Lp14")
    bill = _fetch_bill_detail(db, bid)
    db.close()

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s  # naive pass-through testam
    template = env.get_template("likumprojekts.html.j2")
    html = template.render(bill=bill)

    assert "1315/Lp14" in html
    assert "Grozījumi Aizsardzības likumā" in html
    assert "14. Saeima · Likumprojekts" in html  # pagehead-kicker conditional
    assert "1.lasījums" in html
    assert "3.lasījums" in html
    assert "Ministru kabinets" in html
    assert 'class="bill-detail-timeline"' in html
```

Run → FAIL ar `TemplateNotFound`.

- [ ] **Step 2: Izveido `templates/likumprojekts.html.j2`**

```jinja
{% extends "base.html.j2" %}
{% set active_page = "" %}
{% set assets_prefix = "../" %}

{% block title %}{{ bill.title }} ({{ bill.document_nr }}){% endblock %}

{% block content %}
<section class="pagehead-section">
  <header class="pagehead-header">
    <div class="pagehead-header-title">
      <div class="pagehead-kicker">
        14. Saeima ·
        {% if bill.bill_type == "Lp14" %}Likumprojekts
        {% elif bill.bill_type == "Lm14" %}Lēmuma projekts
        {% elif bill.bill_type == "P14" %}Paziņojums
        {% endif %}
      </div>
      <h1 class="pagehead-h1">{{ bill.title }}</h1>
    </div>
    <div class="pagehead-metrics">
      <div class="pagehead-metric">
        <span class="pagehead-metric-label">Nr.</span>
        <span class="pagehead-metric-value">{{ bill.document_nr }}</span>
      </div>
      {% if bill.topic %}
      <div class="pagehead-metric">
        <span class="pagehead-metric-label">Tēma</span>
        <span class="pagehead-metric-value">{{ bill.topic }}</span>
      </div>
      {% endif %}
      <div class="pagehead-metric">
        <span class="pagehead-metric-label">Statuss</span>
        <span class="pagehead-metric-value">{{ bill.current_status }}</span>
      </div>
    </div>
  </header>
</section>

{% if bill.summary %}
<section class="bill-detail-summary">
  <p>{{ bill.summary }}</p>
</section>
{% endif %}

<section class="bill-detail-timeline-section">
  <h2>Stadijas</h2>
  {% if bill.stages %}
  <ol class="bill-detail-timeline">
    {% for s in bill.stages %}
    <li class="bill-detail-timeline-item">
      <span class="timeline-date">{{ s.stage_date }}</span>
      <span class="timeline-stage">{{ s.stage_name }}</span>
      {% if s.stage_result %}
      <span class="badge {% if s.stage_result == 'pieņemts' %}badge-green{% elif s.stage_result == 'noraidīts' %}badge-red{% else %}badge-muted{% endif %}">{{ s.stage_result }}</span>
      {% endif %}
      {% if s.total_par is not none %}
      <span class="timeline-counts">{{ s.total_par }}/{{ s.total_pret }}/{{ s.total_atturas }}</span>
      {% endif %}
      {% if s.vote_id %}
      <a href="../balsojumi.html#vote-{{ s.vote_id }}" class="timeline-vote-link">balsojums →</a>
      {% endif %}
    </li>
    {% endfor %}
  </ol>
  {% else %}
  <p class="empty-state">Stadiju nav reģistrētas.</p>
  {% endif %}
</section>

<section class="bill-detail-submitters">
  <h2>Iesniedzēji</h2>
  {% if bill.institutional_submitter or bill.submitters_individual %}
  <ul>
    {% if bill.institutional_submitter %}
    <li><strong>{{ bill.institutional_submitter }}</strong> <span class="muted">(institucionāls)</span></li>
    {% endif %}
    {% for p in bill.submitters_individual %}
    <li><a href="../politiki/{{ p.slug }}.html">{{ p.name }}</a>{% if p.party %} <span class="muted">({{ p.party }})</span>{% endif %}</li>
    {% endfor %}
  </ul>
  {% else %}
  <p class="empty-state">Iesniedzējs nav reģistrēts.</p>
  {% endif %}
</section>

<section class="bill-detail-links">
  {% if bill.external_document_url %}
  <a href="{{ bill.external_document_url | safe_url }}" target="_blank" rel="noopener">Oriģinālais dokuments titania.saeima.lv ↗</a>
  {% endif %}
</section>
{% endblock %}
```

- [ ] **Step 3: Run un PASS**

```bash
python -m pytest tests/test_generate_bills.py::test_likumprojekts_template_renders_lp14 -v
```

Sagaidāms: PASS.

- [ ] **Step 4: Lm14 render tests**

```python
def test_likumprojekts_template_renders_lm14(db_with_bills):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _fetch_bill_detail, _safe_url_filter

    db = get_db(db_with_bills)
    bid = next(b["id"] for b in _fetch_bills(db) if b["document_nr"] == "952/Lm14")
    bill = _fetch_bill_detail(db, bid)
    db.close()

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    template = env.get_template("likumprojekts.html.j2")
    html = template.render(bill=bill)

    assert "14. Saeima · Lēmuma projekts" in html
    assert "tiesneša_amats" in html
    # Lm14 not Lp14 — neturētu rādīt lasījumu vārdu
    assert "1.lasījums" not in html
```

Run → PASS.

- [ ] **Step 5: P14 render tests**

Fixture jau ietver P14 bill (`127/P14`) Task 1 Step 1 setup'ā:

```python
def test_likumprojekts_template_renders_p14(db_with_bills):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _fetch_bill_detail, _safe_url_filter

    db = get_db(db_with_bills)
    bid = next(b["id"] for b in _fetch_bills(db) if b["document_nr"] == "127/P14")
    bill = _fetch_bill_detail(db, bid)
    db.close()

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    template = env.get_template("likumprojekts.html.j2")
    html = template.render(bill=bill)

    assert "14. Saeima · Paziņojums" in html
    assert "iesniegts" in html
    assert "paziņojuma_balsojums" in html
    assert "1.lasījums" not in html
```

Run → PASS.

- [ ] **Step 6: Commit**

```bash
git add templates/likumprojekts.html.j2 tests/test_generate_bills.py
git commit -m "$(cat <<'EOF'
feat(templates): likumprojekts.html.j2 — bill detail page (Lp14/Lm14/P14)

bill_type-conditional pagehead-kicker; vertikāla stages timeline ar
stage_result badge un per-stadijas link uz balsojumu; iesniedzēju
sekcija ar institucionālo + individuālo politiķu linkiem; ārējais
titania.saeima.lv linka; empty states bez stadijām/iesniedzējiem.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Bill_card macro `templates/_bill_card.html.j2`

**Files:**
- Create: `templates/_bill_card.html.j2`
- Test: `tests/test_generate_bills.py`

- [ ] **Step 1: Failing testu**

```python
def test_bill_card_macro_renders_required_elements(db_with_bills):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _safe_url_filter

    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    db.close()
    bill = next(b for b in bills if b["document_nr"] == "1315/Lp14")

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    template_str = """
    {% from "_bill_card.html.j2" import bill_card %}
    {{ bill_card(bill) }}
    """
    html = env.from_string(template_str).render(bill=bill)
    assert "1315/Lp14" in html
    assert "Grozījumi Aizsardzības likumā" in html
    assert 'class="bill-card"' in html
    assert 'href="likumprojekti/1315-lp14.html"' in html
    assert 'data-topic="Aizsardzība un drošība"' in html
    assert 'data-bill-type="Lp14"' in html
    assert 'data-status="pieņemts"' in html
```

Run → FAIL `TemplateNotFound`.

- [ ] **Step 2: Izveido `templates/_bill_card.html.j2`**

```jinja
{# Bill card macro — used in /balsojumi.html#bills-list grid; later (1B-ii) on politician profile. #}

{% macro bill_card(bill) %}
<a class="bill-card"
   href="likumprojekti/{{ bill.slug }}.html"
   data-topic="{{ bill.topic or '' }}"
   data-bill-type="{{ bill.bill_type }}"
   data-status="{{ bill.current_status }}"
   data-search="{{ (bill.title ~ ' ' ~ bill.document_nr)|lower }}">
  <div class="bill-card-header">
    <span class="badge bill-pill-{{ bill.bill_type|lower }}">{{ bill.document_nr }}</span>
    {% if bill.topic %}<span class="badge badge-muted">{{ bill.topic }}</span>{% endif %}
  </div>
  <div class="bill-card-body">
    <h3>{{ bill.title }}</h3>
    {% if bill.summary %}<p class="bill-card-summary">{{ bill.summary }}</p>{% endif %}
  </div>
  <div class="bill-card-footer">
    <span class="badge {% if bill.current_status == 'pieņemts' %}badge-green{% elif bill.current_status == 'noraidīts' %}badge-red{% else %}badge-yellow{% endif %}">
      {{ bill.current_stage }}{% if bill.current_status %} · {{ bill.current_status }}{% endif %}
    </span>
    {% if bill.institutional_submitter %}
    <span class="bill-card-submitter">{{ bill.institutional_submitter }}</span>
    {% elif bill.submitter_count %}
    <span class="bill-card-submitter">{{ bill.submitter_count }} iesniedzēj{% if bill.submitter_count == 1 %}s{% else %}i{% endif %}</span>
    {% endif %}
  </div>
</a>
{% endmacro %}
```

- [ ] **Step 3: Run un PASS**

```bash
python -m pytest tests/test_generate_bills.py::test_bill_card_macro_renders_required_elements -v
```

Sagaidāms: PASS.

- [ ] **Step 4: Commit**

```bash
git add templates/_bill_card.html.j2 tests/test_generate_bills.py
git commit -m "$(cat <<'EOF'
feat(templates): _bill_card macro — reusable grid + profile card

Atkārtoti izmantojams Jinja2 macro bills grid'am /balsojumi.html
un (1B-ii) politiķa profila Likumprojekti sekcijai. Emit
data-* atribūti filter aplikācijai client side.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `templates/balsojumi.html.j2` patches (3. subtab + filter UI + JS + cross-link)

**Files:**
- Modify: `templates/balsojumi.html.j2` (vairākas vietas)
- Test: `tests/test_generate_bills.py`

- [ ] **Step 1: Pievieno failing testu balsojumi.html patch**

```python
def test_balsojumi_renders_bills_subtab(db_with_bills, tmp_path):
    """Balsojumi.html ietver 3. subtab + bills-list-tab div + #bills-list grid."""
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _safe_url_filter

    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    db.close()

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    env.filters["safe_json"] = lambda s: "null"
    template = env.get_template("balsojumi.html.j2")
    html = template.render(
        votes=[], deputies=[], vote_topics=[], vote_sessions=[],
        metrics={"total": 0, "last_week": 0, "accepted_pct": 0},
        matrix_data=None, matrix_json=None,
        bills=bills, bill_topics=["Aizsardzība un drošība", "Valsts pārvalde"],
    )
    assert 'data-tab="bills-list"' in html
    assert 'id="bills-list-tab"' in html
    assert 'class="bill-card-grid"' in html
    assert "1315/Lp14" in html  # bill ir grid'ā
    assert "952/Lm14" in html
```

Run → FAIL.

- [ ] **Step 2: Patch subtab bāra (`templates/balsojumi.html.j2:32-35`)**

Pievieno trešo button:
```jinja
  <div class="subtab-bar">
    <button class="subtab-btn active" onclick="window.switchTab('votes-list')" data-tab="votes-list">Balsojumi</button>
    <button class="subtab-btn" onclick="window.switchTab('votes-matrix')" data-tab="votes-matrix">Matrica</button>
    <button class="subtab-btn" onclick="window.switchTab('bills-list')" data-tab="bills-list">Likumprojekti</button>
  </div>
```

- [ ] **Step 3: Pievieno bills-list tab div pirms `</section>` rindas**

Atrod kur beidzas `<div id="votes-matrix-tab" style="display: none;">` (~līnija 252) un PIRMS `</section>` (~līnija 253) pievieno:

```jinja
  <!-- ═══ TAB 3: Bills list ═══ -->
  <div id="bills-list-tab" style="display: none;">
    {% from "_bill_card.html.j2" import bill_card %}
    <div class="filter-bar">
      <div class="multi-select" id="bill-topic-select">
        <div class="multi-select-trigger" id="bill-topic-trigger">
          <span>Visas tēmas</span><span class="arrow">&#9660;</span>
        </div>
        <div class="multi-select-dropdown">
          <input type="text" class="multi-select-search" placeholder="Meklēt..." oninput="filterOptions(this)">
          {% for topic in bill_topics %}
          <div class="multi-select-option" data-value="{{ topic }}">
            <span class="checkbox"></span><span>{{ topic }}</span>
          </div>
          {% endfor %}
          <div class="multi-select-clear">Notīrīt izvēli</div>
        </div>
      </div>

      <div class="bill-status-filter">
        <button class="link-filter-btn active" data-status="" onclick="window.toggleBillStatus(this)">Visi</button>
        <button class="link-filter-btn" data-status="procesā" onclick="window.toggleBillStatus(this)">Procesā</button>
        <button class="link-filter-btn" data-status="pieņemts" onclick="window.toggleBillStatus(this)">Pieņemts</button>
        <button class="link-filter-btn" data-status="noraidīts" onclick="window.toggleBillStatus(this)">Noraidīts</button>
      </div>

      <div class="bill-type-filter">
        {% for bt in ['Lp14', 'Lm14', 'P14'] %}
        <button class="link-filter-btn active" data-bill-type="{{ bt }}" onclick="window.toggleBillType(this)">{{ bt }}</button>
        {% endfor %}
      </div>

      <input type="search" id="bill-search" placeholder="Meklēt nosaukumā..." oninput="window.applyBillsFilters()" class="bill-search-input">
    </div>

    <div class="bill-card-grid" id="bills-grid">
      {% for b in bills %}{{ bill_card(b) }}{% endfor %}
    </div>
    <div id="bills-empty-state" class="votes-empty-state" style="display:none;">
      <span class="empty-icon">&#9638;</span>
      <p>Nav likumprojektu, kas atbilst filtriem</p>
    </div>
  </div>
```

- [ ] **Step 4: Patch JS — extend `switchTab` un pievieno bills filter logic**

Atrod `window.switchTab = function(tab) {` (~līnija 263). Pārraksti uz:

```javascript
  window.switchTab = function(tab) {
    var listTab = document.getElementById('votes-list-tab');
    var matrixTab = document.getElementById('votes-matrix-tab');
    var billsTab = document.getElementById('bills-list-tab');
    var btns = document.querySelectorAll('.subtab-btn');
    btns.forEach(function(b) { b.classList.toggle('active', b.dataset.tab === tab); });
    listTab.style.display = (tab === 'votes-list') ? '' : 'none';
    matrixTab.style.display = (tab === 'votes-matrix') ? '' : 'none';
    if (billsTab) billsTab.style.display = (tab === 'bills-list') ? '' : 'none';
  };
```

Pirms `})();` aizvēršanas (pirms vote-list filter-bar setup beigām, ap līniju 392) pievieno bills filter logic:

```javascript
  // ══════════════════════════════════════
  // Bills list filters
  // ══════════════════════════════════════
  var selectedBillTopics = new Set();
  var selectedBillStatus = '';
  var hiddenBillTypes = new Set();

  window.toggleBillStatus = function(btn) {
    document.querySelectorAll('.bill-status-filter .link-filter-btn').forEach(function(b) {
      b.classList.remove('active');
    });
    btn.classList.add('active');
    selectedBillStatus = btn.dataset.status;
    window.applyBillsFilters();
  };

  window.toggleBillType = function(btn) {
    var bt = btn.dataset.billType;
    btn.classList.toggle('active');
    if (hiddenBillTypes.has(bt)) hiddenBillTypes.delete(bt);
    else hiddenBillTypes.add(bt);
    window.applyBillsFilters();
  };

  window.applyBillsFilters = function() {
    var search = (document.getElementById('bill-search').value || '').toLowerCase();
    var cards = document.querySelectorAll('#bills-grid .bill-card');
    var visible = 0;
    cards.forEach(function(card) {
      var topicOk = selectedBillTopics.size === 0 || selectedBillTopics.has(card.dataset.topic);
      var statusOk = !selectedBillStatus || card.dataset.status === selectedBillStatus;
      var typeOk = !hiddenBillTypes.has(card.dataset.billType);
      var searchOk = !search || (card.dataset.search || '').includes(search);
      var ok = topicOk && statusOk && typeOk && searchOk;
      card.style.display = ok ? '' : 'none';
      if (ok) visible++;
    });
    var empty = document.getElementById('bills-empty-state');
    if (empty) empty.style.display = visible === 0 ? 'block' : 'none';
  };

  // Topic multi-select setup analogiski votes — reuse setupMultiSelect helperi
  if (document.getElementById('bill-topic-select')) {
    setupMultiSelect('bill-topic-select', 'bill-topic-trigger', selectedBillTopics, 'Visas tēmas', 'tēmas izvēlētas');
    // Hook applyBillsFilters call after multi-select changes — vienkārši wrap pēdējo parameter
    // (alternatīvi: rediģē setupMultiSelect lai pieņemtu callback)
  }

  // Switch to bills tab if ?tab=bills
  if (urlParams.get('tab') === 'bills') {
    window.switchTab('bills-list');
  }
```

**Note**: `setupMultiSelect` esošais izsauc `applyFilters()` (vote list); ja gribam, lai bills topic select trigger `applyBillsFilters`, vai nu mainīt `setupMultiSelect` signatūru pieņemt callback parametru, vai duplikēt funkciju. Vienkāršākā: pievieno otru `setupMultiSelect` variantu `setupBillsMultiSelect` ar `applyBillsFilters` callback. Engineer izvēlas mazāk koda izmaiņas.

- [ ] **Step 5: Patch vote-card cross-link (`templates/balsojumi.html.j2:131-140` rajons)**

Atrod blok:
```jinja
        <div style="margin-top:0.5rem; display:flex; gap:1rem; font-size:0.85rem;">
          {% if v.document_url %}
          <a href="{{ v.document_url | safe_url }}" target="_blank" rel="noopener">Likumprojekts{% if v.document_nr %} ({{ v.document_nr }}){% endif %} &#8599;</a>
          {% endif %}
          {% if v.url %}
          <a href="{{ v.url | safe_url }}" target="_blank" rel="noopener">Balsojuma tabula &#8599;</a>
          {% endif %}
        </div>
```

Aizvieto ar:
```jinja
        <div style="margin-top:0.5rem; display:flex; gap:1rem; font-size:0.85rem;">
          {% if v.bill_id and v.bill_slug %}
          <a href="likumprojekti/{{ v.bill_slug }}.html">{{ v.document_nr }}</a>
          {% endif %}
          {% if v.document_url %}
          <a href="{{ v.document_url | safe_url }}" target="_blank" rel="noopener">titania.saeima.lv &#8599;</a>
          {% endif %}
          {% if v.url %}
          <a href="{{ v.url | safe_url }}" target="_blank" rel="noopener">Balsojuma tabula &#8599;</a>
          {% endif %}
        </div>
```

- [ ] **Step 6: Vote-card cross-link testi**

```python
def test_vote_card_internal_link_when_bill_id(db_with_bills):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _safe_url_filter

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    env.filters["safe_json"] = lambda s: "null"
    template = env.get_template("balsojumi.html.j2")
    votes = [{
        "id": 1, "motif": "Test", "vote_date": "2026-01-01", "result": "Pieņemts",
        "topic": "X", "tracked_votes": [], "faction_breakdown": [],
        "total_par": 50, "total_pret": 30, "total_atturas": 10,
        "summary": None, "vote_time": None,
        "document_url": "https://example.com/", "document_nr": "1315/Lp14",
        "url": "https://example.com/v",
        "bill_id": 42, "bill_slug": "1315-lp14",
    }]
    html = template.render(
        votes=votes, deputies=[], vote_topics=[], vote_sessions=[],
        metrics={"total": 0, "last_week": 0, "accepted_pct": 0},
        matrix_data=None, matrix_json=None,
        bills=[], bill_topics=[],
    )
    assert 'href="likumprojekti/1315-lp14.html"' in html


def test_vote_card_no_internal_link_when_null_bill_id(db_with_bills):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _safe_url_filter

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    env.filters["safe_json"] = lambda s: "null"
    template = env.get_template("balsojumi.html.j2")
    votes = [{
        "id": 2, "motif": "Procedurāls", "vote_date": "2026-01-01", "result": "Pieņemts",
        "topic": "X", "tracked_votes": [], "faction_breakdown": [],
        "total_par": 50, "total_pret": 30, "total_atturas": 10,
        "summary": None, "vote_time": None,
        "document_url": None, "document_nr": None, "url": None,
        "bill_id": None, "bill_slug": None,
    }]
    html = template.render(
        votes=votes, deputies=[], vote_topics=[], vote_sessions=[],
        metrics={"total": 0, "last_week": 0, "accepted_pct": 0},
        matrix_data=None, matrix_json=None,
        bills=[], bill_topics=[],
    )
    assert 'likumprojekti/' not in html
```

Run → PASS.

- [ ] **Step 7: Run visi templāta testi**

```bash
python -m pytest tests/test_generate_bills.py -v
```

Visi PASS.

- [ ] **Step 8: Commit**

```bash
git add templates/balsojumi.html.j2 tests/test_generate_bills.py
git commit -m "$(cat <<'EOF'
feat(balsojumi): 3. subtab #bills-list + vote-card iekšējs cross-link

balsojumi.html iegūst trešo subtab "Likumprojekti" ar grid (caur
_bill_card macro) + topic/status/bill_type/text filtriem. Vote-card
document_nr kļūst par iekšēju saiti uz likumprojekti/<slug>.html
ja bill_id nav NULL; ārējais titania.saeima.lv linka pārdēvēts
skaidrāk.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `_generate_bill_pages` + hook `generate_public_site` + balsojumi data context

**Files:**
- Modify: `src/generate.py` — pievieno `_generate_bill_pages`; pielāgo `generate_public_site` lai padod `bills` un `bill_topics` balsojumu lapas template'am

- [ ] **Step 1: Failing tests**

```python
def test_generate_bill_pages_emits_correct_count(db_with_bills, tmp_path):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _generate_bill_pages, _safe_url_filter

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    env.filters["safe_json"] = lambda s: "null"
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    db = get_db(db_with_bills)
    _generate_bill_pages(db, env, output_dir)
    db.close()

    bills_dir = output_dir / "likumprojekti"
    files = sorted(p.name for p in bills_dir.iterdir())
    # Fixture: 4 bills (1315/Lp14, 1098/Lp14, 952/Lm14, 127/P14)
    assert files == ["1098-lp14.html", "127-p14.html", "1315-lp14.html", "952-lm14.html"]

def test_generate_bill_pages_uses_slug_filename(db_with_bills, tmp_path):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _generate_bill_pages, _safe_url_filter

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    env.filters["safe_json"] = lambda s: "null"
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    db = get_db(db_with_bills)
    _generate_bill_pages(db, env, output_dir)
    db.close()

    target = output_dir / "likumprojekti" / "1315-lp14.html"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "1315/Lp14" in content
    assert "Grozījumi Aizsardzības likumā" in content
```

Run → FAIL `ImportError`.

- [ ] **Step 2: Implementē `_generate_bill_pages`**

`src/generate.py` aiz `_fetch_bill_detail` definīcijas:

```python
def _generate_bill_pages(db: sqlite3.Connection, env: "Environment", output_dir: Path) -> int:
    """Render likumprojekti/<slug>.html katram bill. Returns count.

    Uzcel mapi `output_dir/likumprojekti/`. Pieņem env ar filters jau registered.
    """
    bills_dir = output_dir / "likumprojekti"
    bills_dir.mkdir(parents=True, exist_ok=True)
    template = env.get_template("likumprojekts.html.j2")
    bills = _fetch_bills(db)
    count = 0
    for b in bills:
        detail = _fetch_bill_detail(db, b["id"])
        if detail is None:
            logger.warning("_generate_bill_pages: bill_id=%s detail returned None — skip", b["id"])
            continue
        html = template.render(bill=detail)
        target = bills_dir / f"{detail['slug']}.html"
        target.write_text(html, encoding="utf-8")
        count += 1
    logger.info("_generate_bill_pages: wrote %d bill pages to %s", count, bills_dir)
    return count
```

- [ ] **Step 3: Run un PASS**

```bash
python -m pytest tests/test_generate_bills.py::test_generate_bill_pages_emits_correct_count tests/test_generate_bills.py::test_generate_bill_pages_uses_slug_filename -v
```

PASS.

- [ ] **Step 4: Hook `_generate_bill_pages` un `bills` context `generate_public_site`**

Atrod `generate_public_site(...)` (~līnija 2629). Pirms `_generate_politician_pages` izsaukuma pievieno:

```python
    # Saeima Bills (Phase 1B-i)
    bill_count = _generate_bill_pages(db, env, output_dir)
    bills = _fetch_bills(db)
    bill_topics = sorted({b["topic"] for b in bills if b["topic"]})
```

Un atrod, kur balsojumi.html tiek renderēts (`balsojumi.html.j2`). Atjaunini render call lai padod `bills` un `bill_topics`:

```python
    balsojumi_html = balsojumi_template.render(
        ...,  # esošie params
        bills=bills,
        bill_topics=bill_topics,
    )
```

- [ ] **Step 5: Manuālā smoke**

```bash
python -m src.generate
```

Sagaidāms: 0 errors. Verificē:
```bash
ls output/atmina/likumprojekti/ | wc -l
```
Sagaidāms: 91+ failu (pēc Task 0 P14 fix).

- [ ] **Step 6: Commit**

```bash
git add src/generate.py tests/test_generate_bills.py
git commit -m "$(cat <<'EOF'
feat(generate): _generate_bill_pages + generate_public_site hook

Iterē pār saeima_bills, render katram likumprojekts.html.j2 uz
output/atmina/likumprojekti/<slug>.html. Hook'ots pirms
_generate_politician_pages, lai 1B-ii politiķa profila linki
rezolvē. Bills + bill_topics tiek padoti balsojumi.html.j2
3. subtab grid'am.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: CSS (`assets/style.css`)

**Files:**
- Modify: `assets/style.css` — pievieno `.bill-card-*`, `.bill-detail-*`, `.bill-pill-*` (~80 rindas)

- [ ] **Step 1: Pievieno CSS bloks**

`assets/style.css` beigās (vai blakus `.vote-card` esošajām klasēm) pievieno:

```css
/* ═══ Bills (Phase 1B-i) ═══ */

.bill-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.bill-card {
  display: flex;
  flex-direction: column;
  padding: 1rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card-bg);
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s, transform 0.15s;
}

.bill-card:hover {
  border-color: var(--accent);
  transform: translateY(-1px);
}

.bill-card-header {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.6rem;
}

.bill-card-body h3 {
  font-size: 1.05rem;
  line-height: 1.35;
  margin: 0 0 0.4rem;
}

.bill-card-summary {
  font-size: 0.88rem;
  color: var(--text-muted);
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.bill-card-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin-top: auto;
  padding-top: 0.7rem;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.bill-pill-lp14 { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
.bill-pill-lm14 { background: rgba(168, 85, 247, 0.15); color: #a855f7; }
.bill-pill-p14  { background: rgba(34, 197, 94, 0.15);  color: #22c55e; }

.bill-card-submitter {
  font-style: italic;
}

/* Detail page */

.bill-detail-summary {
  font-family: Georgia, serif;
  font-size: 1.125rem;
  line-height: 1.6;
  margin: 1.5rem 0;
  color: var(--text);
}

.bill-detail-timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  border-left: 2px solid var(--border);
}

.bill-detail-timeline-item {
  position: relative;
  padding: 0.5rem 0 0.5rem 1.2rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: center;
  font-size: 0.92rem;
}

.bill-detail-timeline-item::before {
  content: "";
  position: absolute;
  left: -7px;
  top: 0.85rem;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--accent);
}

.timeline-date {
  font-family: var(--font-mono, monospace);
  color: var(--text-muted);
  font-size: 0.85rem;
}

.timeline-stage {
  font-weight: 600;
}

.timeline-counts {
  font-family: var(--font-mono, monospace);
  font-size: 0.82rem;
  color: var(--text-muted);
}

.timeline-vote-link {
  font-size: 0.82rem;
}

.bill-detail-submitters,
.bill-detail-links {
  margin-top: 1.5rem;
}

.bill-detail-submitters ul {
  list-style: none;
  padding: 0;
}

.bill-detail-submitters li {
  padding: 0.3rem 0;
}

.empty-state {
  font-style: italic;
  color: var(--text-muted);
}

/* Bills list filter bar (specific to balsojumi.html#bills-list) */

.bill-status-filter,
.bill-type-filter {
  display: flex;
  gap: 0.3rem;
}

.bill-search-input {
  flex: 1 1 200px;
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--input-bg);
  color: inherit;
}

@media (max-width: 760px) {
  .bill-card-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 2: Manuāli pārbauda lokāli**

```bash
python serve.py
```

Atver `http://127.0.0.1:8080/balsojumi.html` → klikšķis "Likumprojekti" subtab → pārbauda kartiņas, filtri strādā. Klikšķis kartiņa → detail lapa renderē timeline.

- [ ] **Step 3: Commit**

```bash
git add assets/style.css
git commit -m "$(cat <<'EOF'
feat(css): bill-card grid + detail timeline + bill_type pills

~80 rindas CSS Phase 1B-i. .bill-card grid responsive ar
auto-fill minmax(320px,1fr); .bill-detail-timeline vertikāla
ar filled circles; .bill-pill-{lp14,lm14,p14} krāsu varianti
matches balsojumi vote-card stila konvencijām.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Sitemap patch

**Files:**
- Modify: `src/generate.py::_generate_sitemap`

- [ ] **Step 1: Atrod `_generate_sitemap` (~līnija 3691) un nolasa**

Apskata pašreizējo sitemap implementāciju, lai zinātu, kā pievieno URLs.

- [ ] **Step 2: Failing tests**

```python
def test_sitemap_includes_bills_urls(db_with_bills, tmp_path):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _generate_sitemap, _generate_bill_pages, _safe_url_filter

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    env.filters["safe_json"] = lambda s: "null"
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    db = get_db(db_with_bills)
    _generate_bill_pages(db, env, output_dir)
    _generate_sitemap(db, output_dir)
    db.close()

    sitemap = (output_dir / "sitemap.xml").read_text(encoding="utf-8")
    assert "likumprojekti/1315-lp14.html" in sitemap
    assert "likumprojekti/952-lm14.html" in sitemap
```

Run → FAIL.

- [ ] **Step 3: Patch `_generate_sitemap`**

Pievieno bills URL ģenerāciju esošajai sitemap loop'ai:

```python
    # Bills (Phase 1B-i)
    for b in _fetch_bills(db):
        urls.append({
            "loc": f"{BASE_URL}/likumprojekti/{b['slug']}.html",
            "lastmod": (b["last_updated_at"] or "")[:10],
            "priority": "0.6",
        })
```

(Adapt to actual data structure — esošais code var izmantot citu shape.)

- [ ] **Step 4: Run un PASS**

- [ ] **Step 5: Commit**

```bash
git add src/generate.py tests/test_generate_bills.py
git commit -m "$(cat <<'EOF'
feat(generate): sitemap includes /likumprojekti/* URLs

Pievieno N bill detail lapu ierakstus sitemap.xml ar priority 0.6,
lastmod no bill.last_updated_at.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: CHANGELOG + final smoke

**Files:**
- Modify: `wiki/CHANGELOG.md`

- [ ] **Step 1: Pievieno CHANGELOG ierakstu**

`wiki/CHANGELOG.md` augšā (zem H1) pievieno jaunu sekciju:

```markdown
## 2026-04-27 — Saeima Bills Phase 1B-i: UI uz publiku

**Iemesls:** Phase 1A (DB schema + helperi + backfill) tika ievests 2026-04-27 (commit `64f1790`), bet bills datus varēja redzēt tikai caur SQL. Phase 1B-i atver tos publikai.

**Izmaiņas:**

- **Jaunas lapas**: `/likumprojekti/<slug>.html` katram no 91+ saeima_bills (slug = `document_nr.lower().replace("/", "-")`)
- **`/balsojumi.html`**: 3. subtab "Likumprojekti" ar topic/status/bill_type filtriem un teksta meklēšanu
- **Vote-card cross-link**: `document_nr` esošās balsojumu kartiņās kļūst par iekšēju saiti uz attiecīgo bill detail lapu (105 saistīti, 34 procedurālie paliek bez)
- **Step 0 P14 motif fix**: paplašina `_DOCUMENT_NR_RE` lai tver unparenthesized `/P14` motifu — atrisina HANDOFF Phase 0.7 punkts #6

**Atstāts 1B-ii:**
- "Saistītais bāzes likums" detail bloks + wiki/laws/<slug>.md auto-render + politiķa profila Likumprojekti sekcija + `base_law_slug` retro-backfill

**Datu deltas:**
- saeima_bills: 91 → 91+N (kur N = jaunie P14 pēc Step 0)
- Tukšs: junction `saeima_bill_politicians` paliek tukšs līdz 1B-ii vai live aģenta flow
```

- [ ] **Step 2: Run pilna testu suite**

```bash
python -m pytest tests/test_saeima_bills.py tests/test_saeima_bills_integration.py tests/test_generate_bills.py tests/test_generate.py -q
```

Sagaidāms: visi PASS. Ja kāds esošs `test_generate.py` test fail-ē balsojumi.html template render dēļ jaunās context rekvizītes (`bills`, `bill_topics`), pielāgo testu lai padod tukšu `bills=[]`.

- [ ] **Step 3: Pilna ģenerācija**

```bash
python -m src.generate
```

Sagaidāms: 0 errors. Verificē:
```bash
find output/atmina/likumprojekti/ -name "*.html" | wc -l
```
≥91 (vai 91+P14 atkarīgs no Task 0).

- [ ] **Step 4: Manuāla acu pārbaude**

```bash
python serve.py
```

Pārbauda visu acceptance kritēriju saraksts no spec § 13:
- `/balsojumi.html#bills-list` rāda kartiņas, filtri strādā
- klikšķis kartiņa → detail lapa rāda timeline + iesniedzējus
- klikšķis timeline `1.lasījums` rinda → atgriež uz `/balsojumi.html#vote-{id}`
- klikšķis vote-card `document_nr` linku → ved uz detail lapu
- Lm14 detail (piem. `tiesneša_amats`) renderē bez Lp14 specifiskiem blokiem
- P14 detail (pēc Step 0) renderē 2-stadiju timeline

- [ ] **Step 5: Commit**

```bash
git add wiki/CHANGELOG.md
git commit -m "$(cat <<'EOF'
docs(changelog): Phase 1B-i — Saeima Bills UI uz publiku

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6: Push branch**

```bash
git push -u origin saeima-bills-phase-1b-i
```

(Optional — tikai ja gribam PR pirms merge. Citādi atgriežas uz master un izsaucama merge.)

---

## Self-Review Checklist

Pēc plāna pabeigšanas, agentic worker apstiprina:

- [ ] Visi spec § 2.1 elementi ir ietverti vienā no Task 0-8
- [ ] Visi spec § 11 testi ir uzrakstīti
- [ ] Spec § 13 akceptances kritēriji izpildīti
- [ ] Phase 1A 57+ esošie testi joprojām PASS (regression check)
- [ ] `python -m src.generate` 0 errors
- [ ] Manuāla pārbaude pa serve.py — visi 6 kritēriji no Step 4 izpildīti

## Atkarības starp tasks

```
Task 0 (P14 fix) ────────────────────┐
                                      ↓
Task 1 (fetchers) ──┐                 │
                    ├→ Task 2 (detail template) ──┐
                    │                              │
                    ├→ Task 3 (macro) ──┐          │
                    │                    ↓          │
                    ├→ Task 4 (balsojumi.html patches) ──┐
                    │                                     ↓
                    └→ Task 5 (generate hook) ──→ Task 6 (CSS) ──→ Task 7 (sitemap) ──→ Task 8 (CHANGELOG + smoke)
```

Tasks 1-3 var iet paralēli (atsevišķi commits). Task 4 prasa Task 1 (`bill_slug`), Task 3 (macro) un Task 5 (`bills` context). Task 5 prasa Task 1, 2, 3. Task 6 var iet paralēli ar Task 4-5 (CSS ir izolēts). Task 7-8 ir secīgi pēdējie.
