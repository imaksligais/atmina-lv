# "Uzmanības centrā" rotācijas kompozīts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stale landing "Jaunākās pretrunas" section with a 3-slot freshness-fallback composite (Karstā tēma / svaigā pretruna / spriedžu duelis / dienas citāts) that re-computes on every dashboard render.

**Architecture:** New focused module `src/render/focus.py` (pure helpers + slot assembly, hermetically tested) → `src/render/dashboard.py` passes one `focus` context key → `templates/index.html.j2` section swap → `assets/style.css` new `.focus-*` block. Spec: `docs/superpowers/specs/2026-07-07-uzmanibas-centra-rotacija-design.md`.

**Tech Stack:** Python/sqlite3 + Jinja2 SSR, zero JS. Existing idioms only: `_slugify`, `_party_short_name`, `PARTY_COLORS`, `_initials_from_name`, `ASSETS_DIR` photo check, `_domain_from_url` (visi `src/render/_common.py`), `_fetch_tensions` (`src/render/tensions.py`), `get_coalition_map` (`src/coalition.py`), `lv_plural` filtrs, breakpointi 600/768/900.

**Konvencijas (CLAUDE.md):** `claim_type='position'` gate visos vaicājumos; `quote` VERBATIM — nekādu labojumu; audience-izslēgšana `('journalist','organization','neutral','inactive')`; koalīcija tikai caur `parties.coalition_status`; LV gramatikas vārti visiem jaunajiem UI tekstiem.

---

### Task 0: Worktree setup

**Files:** nav (git + fs darbības)

- [ ] **Step 1:** No repo saknes: `git worktree add .worktrees/uzmanibas-centra -b feat/uzmanibas-centra && cd .worktrees/uzmanibas-centra && git rev-parse --abbrev-ref HEAD` — Expected: `feat/uzmanibas-centra`. (Subagenti: CWD jāverificē promptā — `feedback_subagent_cwd_inheritance`.)
- [ ] **Step 2:** DB hardlink (NE simlinks, NE kopija): `ln "~/atmina/data/atmina.db" data/atmina.db` (07-04 redesigna pattern). Python vienmēr caur galvenā repo venv absolūto ceļu: `"~/atmina/.venv/Scripts/python.exe"`.
- [ ] **Step 3:** Smoke: `"~/atmina/.venv/Scripts/python.exe" -c "import sqlite3; print(sqlite3.connect('data/atmina.db').execute('SELECT COUNT(*) FROM claims').fetchone()[0])"` — Expected: skaitlis >500000.

### Task 1: `src/render/focus.py` — `_hot_topic()`

**Files:**
- Create: `src/render/focus.py`
- Create: `tests/test_render_focus.py`

- [ ] **Step 1: Failing test** — `tests/test_render_focus.py`:

```python
"""Hermetic tests for src/render/focus.py (Uzmanības centrā composite)."""
import sqlite3
from pathlib import Path

SCHEMA = (Path(__file__).resolve().parents[1] / "src" / "schema.sql").read_text(encoding="utf-8")


def make_db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def seed_pol(db, pid, name, party=None, rel="tracked"):
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (?,?,?,?)",
        (pid, name, party, rel),
    )


def seed_party(db, name, short, status):
    db.execute(
        "INSERT INTO parties (name, short_name, coalition_status) VALUES (?,?,?)",
        (name, short, status),
    )


def seed_claim(db, pid, topic, sal, quote=None, days_ago=1, url="https://x.com/t/1"):
    db.execute(
        "INSERT INTO claims (opponent_id, topic, stance, confidence, salience, quote,"
        " stated_at, claim_type, source_url)"
        " VALUES (?,?,?,0.8,?,?, DATETIME('now', ?), 'position', ?)",
        (pid, topic, f"stance par {topic}", sal, quote, f"-{days_ago} days", url),
    )


def test_hot_topic_salience_weighted_beats_raw_count():
    """3 poz. ar sal 0.9 (skors 3+3.6=6.6) uzvar 5 poz. ar sal 0.3 (5+1.2=6.2)."""
    from src.render.focus import _hot_topic
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_pol(db, 2, "Jānis Ozols", "Partija B")
    for i in range(5):
        seed_claim(db, 1, "Budžets", 0.3, url=f"https://x.com/b/{i}")
    for i in range(3):
        seed_claim(db, 2, "Vēlēšanas", 0.9, quote="X" * 60, url=f"https://x.com/v/{i}")
    hot = _hot_topic(db)
    assert hot["topic"] == "Vēlēšanas"


def test_hot_topic_excludes_audience_accounts():
    from src.render.focus import _hot_topic
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_pol(db, 9, "LETA", None, rel="journalist")
    seed_claim(db, 1, "Budžets", 0.5, quote="Y" * 50)
    for i in range(9):
        seed_claim(db, 9, "Sports", 0.9, url=f"https://x.com/s/{i}")
    assert _hot_topic(db)["topic"] == "Budžets"


def test_hot_topic_quotes_verbatim_one_per_politician():
    from src.render.focus import _hot_topic
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    typo_quote = "Steidamas izmaiņas ar kļūdu tekstā, kas paliek kā ir!!"
    seed_claim(db, 1, "Vēlēšanas", 0.9, quote=typo_quote, url="https://x.com/q/1")
    seed_claim(db, 1, "Vēlēšanas", 0.8, quote="Otrs citāts tam pašam politiķim garumā ok", url="https://x.com/q/2")
    hot = _hot_topic(db)
    assert [q["quote"] for q in hot["quotes"]] == [typo_quote]  # verbatim + 1/politiķi


def test_hot_topic_coalition_bar_counts_all_positions_not_just_quotes():
    from src.render.focus import _hot_topic
    db = make_db()
    seed_party(db, "Partija A", "PA", "coalition")
    seed_party(db, "Partija B", "PB", "opposition")
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_pol(db, 2, "Jānis Ozols", "Partija B")
    seed_pol(db, 3, "Zenta Liepa", None)  # bezpartejiska → joslā neskaitās
    seed_claim(db, 1, "Vēlēšanas", 0.9, quote="Q" * 50, url="https://x.com/1")
    seed_claim(db, 1, "Vēlēšanas", 0.2, url="https://x.com/2")   # bez quote — joslā TOMĒR skaitās
    seed_claim(db, 2, "Vēlēšanas", 0.4, url="https://x.com/3")
    seed_claim(db, 3, "Vēlēšanas", 0.4, url="https://x.com/4")
    hot = _hot_topic(db)
    assert (hot["koal_n"], hot["opoz_n"]) == (2, 1)
```

- [ ] **Step 2:** Run: `"~/atmina/.venv/Scripts/python.exe" -m pytest tests/test_render_focus.py -q` — Expected: FAIL `No module named 'src.render.focus'`.
- [ ] **Step 3: Implementācija** — `src/render/focus.py`:

```python
"""Uzmanības centrā composite — landing slot data (spec 2026-07-07).

Pure helpers: katrs atgriež dict | None; nekādu rakstīšanu DB. Visi vaicājumi
gated uz claim_type='position' + audience-izslēgšanu (tas pats filtrs kā brief
statistikai). `quote` teksti ir VERBATIM — nekādas normalizācijas (CLAUDE.md
Output Conventions izņēmums).
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any, Optional

from src.coalition import get_coalition_map
from src.render._common import (
    PARTY_COLORS,
    _domain_from_url,
    _initials_from_name,
    _party_short_name,
    _slugify,
    ASSETS_DIR,
)

_AUDIENCE = ("journalist", "organization", "neutral", "inactive")
_SALIENCE_W = 4.0   # skora svars: n + 4*MAX(salience) — 0.85-solo pārspēj 2×0.3
_FRESH_DAYS = 14
_MIN_QUOTE_LEN = 40


def _person_card(name: str, party: Optional[str]) -> dict[str, Any]:
    slug = _slugify(name)
    party = party or ""
    return {
        "name": name,
        "slug": slug,
        "initials": _initials_from_name(name),
        "party_short": _party_short_name(party) if party else "",
        "party_color": PARTY_COLORS.get(party, "#8b8fa3"),
        "has_photo": (ASSETS_DIR / "photos" / f"{slug}.jpg").exists(),
    }


def _hot_topic(db: sqlite3.Connection) -> Optional[dict[str, Any]]:
    """Nedēļas karstākā tēma: skors = n + 4*MAX(salience), izšķirtne → politiķu skaits."""
    rows = db.execute(
        """SELECT c.topic, COUNT(*) n, COUNT(DISTINCT c.opponent_id) pol,
                  MAX(c.salience) maxsal
           FROM claims c JOIN tracked_politicians tp ON tp.id = c.opponent_id
           WHERE c.claim_type = 'position' AND c.stated_at >= DATE('now','-7 days')
             AND tp.relationship_type NOT IN (?,?,?,?)
           GROUP BY c.topic""",
        _AUDIENCE,
    ).fetchall()
    if not rows:
        return None
    best = max(rows, key=lambda r: (r["n"] + _SALIENCE_W * (r["maxsal"] or 0), r["pol"]))
    topic = best["topic"]

    qrows = db.execute(
        """SELECT c.opponent_id, c.quote, c.salience, c.stated_at, c.source_url,
                  tp.name, tp.party
           FROM claims c JOIN tracked_politicians tp ON tp.id = c.opponent_id
           WHERE c.claim_type = 'position' AND c.topic = ?
             AND c.stated_at >= DATE('now','-7 days')
             AND c.quote IS NOT NULL AND LENGTH(c.quote) > ?
             AND tp.relationship_type NOT IN (?,?,?,?)
           ORDER BY c.salience DESC, c.stated_at DESC""",
        (topic, _MIN_QUOTE_LEN, *_AUDIENCE),
    ).fetchall()
    quotes, seen = [], set()
    for r in qrows:
        if r["opponent_id"] in seen:
            continue
        seen.add(r["opponent_id"])
        card = _person_card(r["name"], r["party"])
        card.update({
            "quote": r["quote"],                       # VERBATIM
            "source_url": r["source_url"],
            "source_domain": _domain_from_url(r["source_url"]),
            "date": (r["stated_at"] or "")[:10],
        })
        quotes.append(card)
        if len(quotes) == 3:
            break

    cmap = get_coalition_map(db)
    koal = opoz = 0
    for r in db.execute(
        """SELECT tp.party, COUNT(*) n
           FROM claims c JOIN tracked_politicians tp ON tp.id = c.opponent_id
           WHERE c.claim_type = 'position' AND c.topic = ?
             AND c.stated_at >= DATE('now','-7 days')
             AND tp.relationship_type NOT IN (?,?,?,?)
           GROUP BY tp.party""",
        (topic, *_AUDIENCE),
    ).fetchall():
        status = cmap.get(r["party"] or "")
        if status == "coalition":
            koal += r["n"]
        elif status == "opposition":
            opoz += r["n"]
    return {
        "topic": topic,
        "topic_slug": _slugify(topic),
        "n": best["n"],
        "pol": best["pol"],
        "quotes": quotes,
        "koal_n": koal,
        "opoz_n": opoz,
    }
```

- [ ] **Step 4:** Run: `... -m pytest tests/test_render_focus.py -q` — Expected: 4 passed. NB: ja `get_coalition_map` atslēgu formas nesakrīt (pilnais vs īsais nosaukums) un tests 4 krīt — lieto to pašu rezolūciju kā `src/render/_common.py::_party_slug_map` dara renderiem; skaties `src/coalition.py` docstring.
- [ ] **Step 5: Commit** — `git add src/render/focus.py tests/test_render_focus.py && git commit -m "feat(focus): _hot_topic — salience-svērtā nedēļas tēma ar citātu kartēm"`

### Task 2: `_quote_of_day()` + `_fresh_tension()`

**Files:** Modify: `src/render/focus.py` · Test: `tests/test_render_focus.py`

- [ ] **Step 1: Failing tests** (pievieno failam):

```python
def test_quote_of_day_falls_back_to_7d_window():
    from src.render.focus import _quote_of_day
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_claim(db, 1, "Budžets", 0.9, quote="Vakardienas spēcīgais citāts pietiekamā garumā", days_ago=3)
    q = _quote_of_day(db)
    assert q and q["quote"].startswith("Vakardienas")


def test_fresh_tension_filters_14d_window():
    from src.render.focus import _fresh_tension
    old = {"created_at": "2026-01-01 10:00:00"}
    new = {"created_at": "2026-07-06 10:00:00", "source_name": "A", "target_name": "B"}
    assert _fresh_tension([old], today=date(2026, 7, 7)) is None
    assert _fresh_tension([new, old], today=date(2026, 7, 7)) is new
```

(augšā failā: `from datetime import date`)

- [ ] **Step 2:** Run — Expected: FAIL (nav funkciju).
- [ ] **Step 3: Implementācija** (pievieno `focus.py`):

```python
def _quote_of_day(db: sqlite3.Connection) -> Optional[dict[str, Any]]:
    """Dienas (fallback: 7d) augstākās salience pozīcija ar kvalitatīvu citātu."""
    for window in ("-1 days", "-7 days"):
        r = db.execute(
            """SELECT c.quote, c.salience, c.stated_at, c.source_url, c.topic,
                      tp.name, tp.party
               FROM claims c JOIN tracked_politicians tp ON tp.id = c.opponent_id
               WHERE c.claim_type = 'position' AND c.stated_at >= DATE('now', ?)
                 AND c.quote IS NOT NULL AND LENGTH(c.quote) > ?
                 AND tp.relationship_type NOT IN (?,?,?,?)
               ORDER BY c.salience DESC, c.stated_at DESC LIMIT 1""",
            (window, _MIN_QUOTE_LEN, *_AUDIENCE),
        ).fetchone()
        if r:
            card = _person_card(r["name"], r["party"])
            card.update({
                "quote": r["quote"],                   # VERBATIM
                "topic": r["topic"],
                "source_url": r["source_url"],
                "source_domain": _domain_from_url(r["source_url"]),
                "date": (r["stated_at"] or "")[:10],
            })
            return card
    return None


def _fresh_tension(tensions: list[dict[str, Any]], today: Optional[date] = None) -> Optional[dict[str, Any]]:
    """Jaunākā spriedze <14d no jau nofetčotā _fetch_tensions saraksta (bez jauna SQL)."""
    cutoff = ((today or date.today()) - timedelta(days=_FRESH_DAYS)).isoformat()
    for t in tensions:  # saraksts jau DESC pēc created_at
        if (t.get("created_at") or "")[:10] >= cutoff:
            return t
    return None
```

- [ ] **Step 4:** Run: `... -m pytest tests/test_render_focus.py -q` — Expected: 6 passed.
- [ ] **Step 5: Commit** — `git commit -am "feat(focus): _quote_of_day + _fresh_tension (14d logs)"`

### Task 3: `assemble_focus()` — slotu fallback ķēde

**Files:** Modify: `src/render/focus.py` · Test: `tests/test_render_focus.py`

- [ ] **Step 1: Failing tests** — 4 stāvokļi:

```python
HOT = {"topic": "Vēlēšanas", "quotes": [{"source_url": "https://x.com/v/0"}]}
CON_FRESH = {"detected_at": "2026-07-06 17:40:18", "id": 42}
CON_OLD = {"detected_at": "2026-05-01 10:00:00", "id": 7}
TEN = {"created_at": "2026-07-05 10:00:00", "source_name": "A", "target_name": "B"}
QOD = {"quote": "Dienas citāts", "source_url": "https://x.com/q/9"}
TODAY = date(2026, 7, 7)


def _kinds(focus):
    return (focus["slot_b"] and focus["slot_b"]["kind"],
            focus["slot_c"] and focus["slot_c"]["kind"])


def test_assemble_fresh_contradiction_and_tension():
    from src.render.focus import assemble_focus
    f = assemble_focus(HOT, [CON_FRESH, CON_OLD], [TEN], QOD, today=TODAY)
    assert _kinds(f) == ("contradiction", "tension")
    assert f["slot_b"]["item"]["id"] == 42


def test_assemble_stale_contradiction_promotes_tension_then_quote():
    from src.render.focus import assemble_focus
    f = assemble_focus(HOT, [CON_OLD], [TEN], QOD, today=TODAY)
    assert _kinds(f) == ("tension", "quote")


def test_assemble_only_quote():
    from src.render.focus import assemble_focus
    f = assemble_focus(HOT, [CON_OLD], [], QOD, today=TODAY)
    assert _kinds(f) == ("quote", None)


def test_assemble_quote_never_duplicates_hot_topic_quote():
    from src.render.focus import assemble_focus
    dup = {"quote": "x", "source_url": "https://x.com/v/0"}  # jau A slotā
    f = assemble_focus(HOT, [CON_OLD], [], dup, today=TODAY)
    assert f["slot_b"] is None and f["slot_c"] is None
```

- [ ] **Step 2:** Run — Expected: FAIL.
- [ ] **Step 3: Implementācija:**

```python
def assemble_focus(
    hot: Optional[dict[str, Any]],
    contradictions: list[dict[str, Any]],
    tensions: list[dict[str, Any]],
    quote_of_day: Optional[dict[str, Any]],
    today: Optional[date] = None,
) -> dict[str, Any]:
    """Slotu ķēde: B = pretruna(<14d) → spriedze(<14d) → citāts; C = spriedze → citāts → None.

    `contradictions` = orchestratora jau padotais enriched saraksts (satur
    detected_at; DESC). Citāts nekad nedublē A slota citātu (source_url).
    """
    cutoff = ((today or date.today()) - timedelta(days=_FRESH_DAYS)).isoformat()
    fresh_c = next(
        (c for c in contradictions if (c.get("detected_at") or "")[:10] >= cutoff), None
    )
    fresh_t = _fresh_tension(tensions, today=today)
    used_urls = {q.get("source_url") for q in (hot or {}).get("quotes", [])}
    qod = quote_of_day if (quote_of_day and quote_of_day.get("source_url") not in used_urls) else None

    slot_b = slot_c = None
    if fresh_c:
        slot_b = {"kind": "contradiction", "item": fresh_c}
    elif fresh_t:
        slot_b, fresh_t = {"kind": "tension", "item": fresh_t}, None
    elif qod:
        slot_b, qod = {"kind": "quote", "item": qod}, None
    if fresh_t:
        slot_c = {"kind": "tension", "item": fresh_t}
    elif qod:
        slot_c = {"kind": "quote", "item": qod}
    return {"hot": hot, "slot_b": slot_b, "slot_c": slot_c}
```

- [ ] **Step 4:** Run: `... -m pytest tests/test_render_focus.py -q` — Expected: 10 passed.
- [ ] **Step 5: Commit** — `git commit -am "feat(focus): assemble_focus slotu fallback ķēde"`

### Task 4: dashboard.py savienojums

**Files:** Modify: `src/render/dashboard.py` (konteksta salikums ap :339)

- [ ] **Step 1:** Importi faila augšā: `from src.render.focus import _hot_topic, _quote_of_day, assemble_focus` un `from src.render.tensions import _fetch_tensions`.
- [ ] **Step 2:** `render_dashboard()` pirms `_render_page(env, "index.html.j2", ...)`:

```python
    # Uzmanības centrā composite (spec 2026-07-07) — visi dati re-compute
    # katrā renderā; contradictions = jau padotais enriched saraksts.
    focus = assemble_focus(
        _hot_topic(db), contradictions, _fetch_tensions(db), _quote_of_day(db)
    )
```

un konteksta dict pievieno `"focus": focus,` (blakus `"latest_contradictions"`, kas PALIEK — to noņems Task 5 kopā ar veco sekciju, ja pēc template maiņas vairs nelieto; pārbaudi ar `grep -n latest_contradictions templates/index.html.j2`).
- [ ] **Step 3:** Smoke uz dzīvās DB (worktree hardlink): `"~/atmina/.venv/Scripts/python.exe" -c "import sqlite3; from src.render.focus import _hot_topic, _quote_of_day; db=sqlite3.connect('data/atmina.db'); db.row_factory=sqlite3.Row; h=_hot_topic(db); print(h['topic'], h['n'], h['pol'], len(h['quotes']), h['koal_n'], h['opoz_n']); print(_quote_of_day(db)['name'])"` — Expected: reāla tēma (piem. `Vēlēšanas 18 14 3 ...`) + politiķa vārds, bez exception.
- [ ] **Step 4: Commit** — `git commit -am "feat(dashboard): focus konteksts index renderam"`

### Task 5: Templote + CSS

**Files:** Modify: `templates/index.html.j2` (sekcija no `<section class="section">` ar virsrakstu `Jaun&#257;k&#257;s pretrunas`, ~:133 līdz tās `</section>`) · Modify: `assets/style.css`

- [ ] **Step 1:** Šīs sekcijas iekšpusē ESOŠO `<article class="prv2-card ...">…</article>` bloku (pilno cikla ķermeni, ~:143–235) IZGRIEZ un saglabā — tas kļūs par B slota pretrunas karti nemainītā veidā. Seno `{% for c in latest_contradictions %}` ciklu un sekcijas galvu aizstāj ar:

```jinja2
{% macro focus_quote_card(q) %}
<article class="focus-quote-card" style="--pc: {{ q.party_color }}">
  <blockquote class="focus-quote-text">{{ q.quote }}</blockquote>
  <footer class="focus-quote-attr">
    {%- if q.has_photo %}
    <img class="prv2-avatar prv2-avatar-photo focus-avatar" src="{{ assets_prefix }}assets/photos/{{ q.slug }}.jpg" alt="{{ q.name }}" width="40" height="40" loading="lazy" style="--pc: {{ q.party_color }}">
    {%- else %}
    <span class="prv2-avatar focus-avatar" style="--pc: {{ q.party_color }}">{{ q.initials }}</span>
    {%- endif %}
    <div class="focus-quote-who">
      <a href="politiki/{{ q.slug }}.html">{{ q.name }}</a>
      <span class="focus-quote-meta">{{ q.party_short }}{% if q.party_short %} · {% endif %}{{ q.date }} · <a href="{{ q.source_url }}" rel="noopener">{{ q.source_domain }} ↗</a></span>
    </div>
  </footer>
</article>
{% endmacro %}

<section class="section">
  <div class="section-head">
    <div>
      <div class="section-head-kicker">Karstākais šobrīd</div>
      <h2 class="section-head-title">Uzmanības centrā</h2>
    </div>
    <a href="pretrunas.html" class="section-head-link">Visas pretrunas &rarr;</a>
  </div>
  <div class="focus-grid{% if not focus.slot_b and not focus.slot_c %} focus-grid-solo{% endif %}">

    {% if focus.hot %}
    <article class="focus-hot">
      <div class="focus-hot-head">
        <span class="focus-hot-flame" aria-hidden="true">🔥</span>
        <div>
          <div class="focus-kicker">Karstā tēma</div>
          <h3 class="focus-hot-title"><a href="temas/{{ focus.hot.topic_slug }}.html">{{ focus.hot.topic }}</a></h3>
        </div>
        <div class="focus-hot-chips">
          <span class="focus-chip">{{ focus.hot.n|lv_plural("pozīcija", "pozīcijas") }}</span>
          <span class="focus-chip">{{ focus.hot.pol|lv_plural("politiķis", "politiķi") }}</span>
          <span class="focus-chip focus-chip-dim">šonedēļ</span>
        </div>
      </div>
      {% for q in focus.hot.quotes %}{{ focus_quote_card(q) }}{% endfor %}
      {% if focus.hot.koal_n or focus.hot.opoz_n %}
      <div class="focus-bloc-bar" role="img" aria-label="Koalīcija {{ focus.hot.koal_n }}, opozīcija {{ focus.hot.opoz_n }}">
        <span class="focus-bloc-koal" style="flex-grow: {{ focus.hot.koal_n }}"></span>
        <span class="focus-bloc-opoz" style="flex-grow: {{ focus.hot.opoz_n }}"></span>
      </div>
      <div class="focus-bloc-legend"><span>Koalīcija {{ focus.hot.koal_n }}</span><span>Opozīcija {{ focus.hot.opoz_n }}</span></div>
      {% endif %}
      <a class="focus-cta" href="temas/{{ focus.hot.topic_slug }}.html">Visa tēma &rarr;</a>
    </article>
    {% endif %}

    {% for slot in [focus.slot_b, focus.slot_c] %}
    {% if slot %}
    <div class="focus-slot">
      {% if slot.kind == 'contradiction' %}
      {% set c = slot.item %}
      <div class="focus-kicker">≈ Svaiga pretruna</div>
      {# ŠEIT ielīmē Task 5 Step 1 izgriezto prv2-card bloku nemainītā veidā #}
      {% elif slot.kind == 'tension' %}
      {% set t = slot.item %}
      <div class="focus-kicker">⚡ {{ t.type_lv }}</div>
      <article class="focus-duel">
        <div class="focus-duel-pair">
          <a class="focus-duel-name" href="politiki/{{ t.source_slug }}.html">{{ t.source_name }}</a>
          <span class="focus-duel-arrow" aria-hidden="true">⟶</span>
          <a class="focus-duel-name" href="politiki/{{ t.target_slug }}.html">{{ t.target_name }}</a>
        </div>
        <p class="focus-duel-desc">{{ t.description }}</p>
        <div class="focus-duel-meta">{{ t.date }}{% if t.topic %} · {{ t.topic }}{% endif %} · <a href="spriedzes.html">Visas spriedzes &rarr;</a></div>
      </article>
      {% elif slot.kind == 'quote' %}
      <div class="focus-kicker">Dienas citāts</div>
      {{ focus_quote_card(slot.item) }}
      {% endif %}
    </div>
    {% endif %}
    {% endfor %}

  </div>
</section>
```

NB: `latest_contradictions` pēc maiņas templotē vairs nav — izņem to arī no `render_dashboard` konteksta dict (`grep -n latest_contradictions` templotē = 0 pēc maiņas; hero_contradictions PALIEK, tas ir cits bloks).
- [ ] **Step 2:** `assets/style.css` — jauns bloks (esošie toņi caur mainīgajiem; breakpoints 900px pēc kanoniskās skalas):

```css
/* ── Uzmanības centrā composite (spec 2026-07-07) ─────────────── */
.focus-grid { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 16px; align-items: start; }
.focus-grid-solo { grid-template-columns: 1fr; }
.focus-hot, .focus-slot { background: var(--card-bg, var(--bg-2, #16181d)); border: 1px solid var(--card-border, rgba(255,255,255,.07)); border-radius: 12px; padding: 18px; }
.focus-hot-head { display: flex; gap: 12px; align-items: flex-start; margin-bottom: 12px; }
.focus-hot-flame { font-size: 1.4rem; line-height: 1; }
.focus-hot-title { margin: 2px 0 0; font-size: 1.35rem; }
.focus-hot-title a { color: inherit; text-decoration: none; }
.focus-hot-chips { margin-left: auto; display: flex; gap: 6px; flex-wrap: wrap; }
.focus-chip { font-size: .72rem; padding: 3px 9px; border-radius: 999px; border: 1px solid var(--card-border, rgba(255,255,255,.12)); white-space: nowrap; }
.focus-chip-dim { opacity: .65; }
.focus-kicker { font-size: .7rem; text-transform: uppercase; letter-spacing: .08em; opacity: .7; margin-bottom: 8px; }
.focus-quote-card { border-left: 3px solid var(--pc, #8b8fa3); padding: 10px 12px; margin: 10px 0; background: color-mix(in srgb, var(--pc, #8b8fa3) 6%, transparent); border-radius: 0 8px 8px 0; }
.focus-quote-text { margin: 0 0 8px; font-style: italic; font-size: .95rem; }
.focus-quote-attr { display: flex; gap: 10px; align-items: center; }
.focus-avatar { width: 40px; height: 40px; font-size: .8rem; }
.focus-quote-who a { font-weight: 600; text-decoration: none; }
.focus-quote-meta { display: block; font-size: .75rem; opacity: .75; }
.focus-bloc-bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 12px; }
.focus-bloc-koal { background: var(--accent, #90A4AE); }
.focus-bloc-opoz { background: #c25e5e; }
.focus-bloc-legend { display: flex; justify-content: space-between; font-size: .72rem; opacity: .75; margin-top: 4px; }
.focus-cta { display: inline-block; margin-top: 12px; font-size: .85rem; }
.focus-duel-pair { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; font-weight: 600; }
.focus-duel-arrow { opacity: .6; }
.focus-duel-desc { font-size: .88rem; margin: 8px 0; }
.focus-duel-meta { font-size: .75rem; opacity: .75; }
@media (max-width: 900px) { .focus-grid { grid-template-columns: 1fr; } }
```

Gaišajā tēmā pārbaudi kontrastu: ja `--card-bg`/`--card-border` mainīgo nav (skaties `:root` un `[data-theme]` blokus style.css sākumā — lieto tos PAŠUS mainīgo vārdus, kādus lieto `.prv2-card`), aizstāj ar eksistējošajiem. `#c25e5e` opozīcijas tonis — pārbaudi AA pret kartes fonu abās tēmās; ja neiziet, `color-mix(in srgb, #c25e5e 80%, var(--text))`.
- [ ] **Step 3:** Renders: `"~/atmina/.venv/Scripts/python.exe" -m src.render --only=dashboard` — Expected: exit 0. `grep -c "section-head-title" output/atmina/index.html` — Expected: 6 (nemainīgs); `grep -c "Uzman" output/atmina/index.html` ≥1; `grep -c "Jaunākās pretrunas" output/atmina/index.html` = 0.
- [ ] **Step 4: Commit** — `git commit -am "feat(landing): Uzmanības centrā rotācijas kompozīts pretrunu sekcijas vietā"`

### Task 6: Vizuālā + pilnā verifikācija

**Files:** nav jaunu (pārbaudes)

- [ ] **Step 1:** Playwright (MCP) uz `output/atmina/index.html` (file:// vai `python -m http.server`): pilnas lapas ekrānuzņēmumi **1440px UN 375px, gaišajā UN tumšajā tēmā** — 4 gab. SVARĪGI: horizontālā scroll pārbaudi (`document.documentElement.scrollWidth <= window.innerWidth`) dari ar SVAIGU ielādi katrā viewport, NE ar resize (07-04 mācība: Chart.js canvas pēc resize dod stale scrollWidth).
- [ ] **Step 2:** Acu pārbaude ekrānuzņēmumos: A slots ar citātiem + joslu; B slots (šobrīd jābūt pretrunai — #42 detected 07-06 <14d); C slots (spriedze vai citāts); 375px stack bez pārplūdes; abās tēmās kontrasts lasāms. Ekrānuzņēmumus parādi operatoram.
- [ ] **Step 3:** Pilnie testi: `"~/atmina/.venv/Scripts/python.exe" -m pytest tests -q` — Expected: pass, IZŅEMOT char-baseline testus, kas legāli drift (index mainījās). Baseline REGEN: `REGEN=1 "~/atmina/.venv/Scripts/python.exe" -m pytest tests -q` (bash env prefikss), tad atkārto bez REGEN — Expected: viss zaļš.
- [ ] **Step 4:** `bash scripts/check.sh` — Expected: exit 0 (ruff + pytest + render smoke).
- [ ] **Step 5: Commit** — `git commit -am "test(landing): focus kompozīta baselines"`

### Task 7: Nobeigums

- [ ] **Step 1:** REQUIRED SUB-SKILL: superpowers:finishing-a-development-branch — merge `feat/uzmanibas-centra` → master, worktree izņemšana.
- [ ] **Step 2:** Master: `python -m src.render --only=dashboard` + `bash scripts/deploy.sh --dry-run --no-delete` → parādi operatoram → **AskUserQuestion deploy apstiprinājums** (publish-pause standing rule) → `bash scripts/deploy.sh --no-delete`.
- [ ] **Step 3:** Live pārbaude: atmina.lv sekcija redzama, citātu avotu saites atveras, temas CTA strādā.
