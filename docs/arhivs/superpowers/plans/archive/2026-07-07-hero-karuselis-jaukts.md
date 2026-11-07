# Hero karuseļa jauktais saturs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hero karuselis (`index.html` "Uzmanības centrā" rotācija) rotē jauktu saturu — pretrunas + spilgtas svaigas pozīcijas + Saeimas balsojumi — pretrunu-tikai vietā.

**Architecture:** Jauna tīra funkcija `hero_feed()` `src/render/focus.py` uzbūvē ≤6 `{kind, item}` sarakstu no jau nofetčotiem datiem (pretrunas no `hero_cards`, balsojumi no `votes`; vienīgais jaunais SQL — pozīciju vaicājums). Šablons renderē trīs kartīšu veidus vienā `hero-feature-card` rāmī; rotācijas JS bez izmaiņām; CSS pāriet uz grid-stack, lai augstums nelēkā.

**Tech Stack:** Python 3 + sqlite3 (bez ORM), Jinja2, tīrs CSS. Testi: pytest, hermētiska `:memory:` DB no `src/schema.sql`.

**Spec:** `docs/superpowers/specs/2026-07-07-hero-karuselis-jaukts-design.md`

**Konteksts izpildītājam bez priekšzināšanām:**
- `src/render/focus.py` — landing "Uzmanības centrā" datu helperi (tīri, bez DB rakstīšanas). Tur jau ir `_person_card`, `_AUDIENCE`, `_FRESH_DAYS=14`, `_MIN_QUOTE_LEN=40`, `today_lv`.
- `src/render/dashboard.py::render_dashboard` saņem `contradictions` (enriched, DESC pēc `detected_at`) un `votes` (`_fetch_votes` rezultāts, DESC pēc `vote_date, vote_time`; katram ir `id`, `vote_date`, `summary`, `motif`, `total_par/pret/atturas`, `result`).
- `hero_cards` = `contradictions[:5]` kopijas ar `old_excerpt`/`new_excerpt` (būvē `render_dashboard`, rindas ~335–340) — TĀS paliek; `hero_feed` no tām ņem pretrunu kartītes.
- `claims.quote` ir VERBATIM — nekādu labojumu (CLAUDE.md vārtu izņēmums).
- LV laika robežas caur `today_lv()`, ne `DATE('now')` (UTC slazds).
- `Nebalsoja`/`Nereģistrējies`/`Reģistrējies` NAV balsis — joslā tikai Par/Pret/Atturas.

---

### Task 1: `hero_feed` testi (failing)

**Files:**
- Modify: `tests/test_render_focus.py` (pievieno bloku faila beigās)

- [ ] **Step 1.1: Pievieno testus faila beigās**

```python
# ── hero_feed (jauktais hero karuselis, spec 2026-07-07) ─────────────────

from datetime import timedelta


def _detected(days_ago: int) -> str:
    from src.db import today_lv
    return (today_lv() - timedelta(days=days_ago)).isoformat() + " 10:00:00"


def con(cid, days_ago):
    """Minimāla hero_cards pretrunu kartīte — hero_feed skatās tikai detected_at."""
    return {"id": cid, "detected_at": _detected(days_ago)}


def vote(vid, par=50, pret=30, att=5, result="Pieņemts", summary="Balsojums X", motif=None):
    return {"id": vid, "vote_date": "2026-06-18", "summary": summary, "motif": motif,
            "total_par": par, "total_pret": pret, "total_atturas": att, "result": result}


EMPTY_FOCUS = {"hot": None, "slot_b": None, "slot_c": None}


def test_hero_feed_fresh_contradictions_capped_at_two():
    from src.render.focus import hero_feed
    db = make_db()
    feed = hero_feed(db, [con(1, 1), con(2, 2), con(3, 3)], [], EMPTY_FOCUS)
    ids = [i["item"]["id"] for i in feed if i["kind"] == "contradiction"]
    assert ids == [1, 2]


def test_hero_feed_stale_contradictions_keep_one_anchor():
    from src.render.focus import hero_feed
    db = make_db()
    feed = hero_feed(db, [con(1, 60), con(2, 90)], [], EMPTY_FOCUS)
    ids = [i["item"]["id"] for i in feed if i["kind"] == "contradiction"]
    assert ids == [1]


def test_hero_feed_votes_filter_zero_ballots_and_dedup_summary():
    from src.render.focus import hero_feed
    db = make_db()
    votes = [
        vote(1, par=0, pret=0, att=0, summary="Kvoruma reģistrācija"),  # 0 balsis → ārā
        vote(2, summary="Grozījumi likumā"),
        vote(3, summary="Grozījumi likumā"),                            # dublēta summary → ārā
        vote(4, summary="Cits balsojums"),
        vote(5, summary="Trešais balsojums"),                           # limit 2 → ārā
    ]
    feed = hero_feed(db, [], votes, EMPTY_FOCUS)
    ids = [i["item"]["id"] for i in feed if i["kind"] == "vote"]
    assert ids == [2, 4]


def test_hero_feed_vote_without_result_skipped():
    from src.render.focus import hero_feed
    db = make_db()
    feed = hero_feed(db, [], [vote(1, result=None)], EMPTY_FOCUS)
    assert feed == []


def test_hero_feed_positions_dedup_focus_urls_and_one_per_politician():
    from src.render.focus import hero_feed
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_pol(db, 2, "Jānis Ozols", "Partija B")
    seed_claim(db, 1, "Budžets", 0.9, quote="A" * 50, url="https://x.com/hot/1")  # jau kompozītā
    seed_claim(db, 1, "Vēlēšanas", 0.8, quote="B" * 50, url="https://x.com/a/2")
    seed_claim(db, 1, "Nodokļi", 0.7, quote="C" * 50, url="https://x.com/a/3")    # 2. tam pašam politiķim → ārā
    seed_claim(db, 2, "Budžets", 0.6, quote="D" * 50, url="https://x.com/b/1")
    focus = {"hot": {"quotes": [{"source_url": "https://x.com/hot/1"}]},
             "slot_b": None, "slot_c": None}
    feed = hero_feed(db, [], [], focus)
    pos = [i["item"] for i in feed if i["kind"] == "position"]
    assert [p["source_url"] for p in pos] == ["https://x.com/a/2", "https://x.com/b/1"]


def test_hero_feed_position_skips_slot_quote_url():
    from src.render.focus import hero_feed
    db = make_db()
    seed_pol(db, 1, "Anna Bērza", "Partija A")
    seed_claim(db, 1, "Budžets", 0.9, quote="A" * 50, url="https://x.com/q/9")
    focus = {"hot": None, "slot_b": {"kind": "quote", "item": {"source_url": "https://x.com/q/9"}},
             "slot_c": None}
    feed = hero_feed(db, [], [], focus)
    assert [i for i in feed if i["kind"] == "position"] == []


def test_hero_feed_interleaves_and_caps_at_six():
    from src.render.focus import hero_feed
    db = make_db()
    for pid in (1, 2, 3):
        seed_pol(db, pid, f"Politiķis {pid}", "Partija A")
        seed_claim(db, pid, "Budžets", 0.9, quote="Q" * 50, url=f"https://x.com/p/{pid}")
    cons = [con(1, 1), con(2, 2)]
    votes = [vote(1, summary="Pirmais"), vote(2, summary="Otrais")]
    feed = hero_feed(db, cons, votes, EMPTY_FOCUS)
    kinds = [i["kind"] for i in feed]
    assert kinds == ["contradiction", "position", "vote",
                     "contradiction", "position", "vote"]  # sāk ar pretrunu; pos_limit=6-2-2=2


def test_hero_feed_position_gets_third_slot_when_others_underfill():
    from src.render.focus import hero_feed
    db = make_db()
    for pid in (1, 2, 3, 4):
        seed_pol(db, pid, f"Politiķis {pid}", "Partija A")
        seed_claim(db, pid, "Budžets", 0.9, quote="Q" * 50, url=f"https://x.com/p/{pid}")
    feed = hero_feed(db, [con(1, 1)], [vote(1)], EMPTY_FOCUS)
    kinds = [i["kind"] for i in feed]
    assert kinds.count("position") == 3 and len(feed) == 5


def test_hero_feed_all_empty_returns_empty():
    from src.render.focus import hero_feed
    db = make_db()
    assert hero_feed(db, [], [], EMPTY_FOCUS) == []
```

- [ ] **Step 1.2: Pārliecinies, ka testi krīt pareizā vietā**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_focus.py -v -k hero_feed`
Expected: visi jaunie testi FAIL ar `ImportError: cannot import name 'hero_feed'`

### Task 2: `hero_feed` implementācija

**Files:**
- Modify: `src/render/focus.py` (pievieno faila beigās, aiz `assemble_focus`)

- [ ] **Step 2.1: Pievieno četras funkcijas `src/render/focus.py` beigās**

```python
def _focus_used_urls(focus: Optional[dict[str, Any]]) -> set:
    """source_url kopa, ko kompozīts jau rāda (karstās tēmas citāti + citātu sloti)."""
    focus = focus or {}
    urls = {q.get("source_url") for q in ((focus.get("hot") or {}).get("quotes") or [])}
    for slot in (focus.get("slot_b"), focus.get("slot_c")):
        if slot and slot.get("kind") == "quote":
            urls.add(slot["item"].get("source_url"))
    urls.discard(None)
    return urls


def _top_positions(
    db: sqlite3.Connection,
    exclude_urls: set,
    limit: int,
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Spilgtākās 7d pozīcijas ar citātu — viena uz politiķi, bez kompozīta dubļiem."""
    cutoff = ((today or today_lv()) - timedelta(days=7)).isoformat()
    rows = db.execute(
        """SELECT c.opponent_id, c.quote, c.topic, c.stated_at, c.source_url,
                  tp.name, tp.party
           FROM claims c JOIN tracked_politicians tp ON tp.id = c.opponent_id
           WHERE c.claim_type = 'position' AND c.stated_at >= ?
             AND c.quote IS NOT NULL AND LENGTH(c.quote) > ?
             AND tp.relationship_type NOT IN (?,?,?,?)
           ORDER BY c.salience DESC, c.stated_at DESC, c.id DESC""",
        (cutoff, _MIN_QUOTE_LEN, *_AUDIENCE),
    ).fetchall()
    out, seen = [], set()
    for r in rows:
        if r["opponent_id"] in seen or r["source_url"] in exclude_urls:
            continue
        seen.add(r["opponent_id"])
        card = _person_card(r["name"], r["party"])
        card.update({
            "quote": r["quote"],                       # VERBATIM
            "topic": r["topic"],
            "source_url": r["source_url"],
            "source_domain": _domain_from_url(r["source_url"]),
            "date": (r["stated_at"] or "")[:10],
        })
        out.append(card)
        if len(out) == limit:
            break
    return out


def _hero_votes(votes: list[dict[str, Any]], limit: int = 2) -> list[dict[str, Any]]:
    """Jaunākie izceļamie balsojumi: ar rezultātu un balsīm, dedup pēc summary.

    Bez svaiguma loga — Saeimai ir brīvlaiki; datums kartītē vienmēr redzams.
    0/0/0 rindas ir procedurālas reģistrācijas, ne balsojumi.
    """
    out, seen = [], set()
    for v in votes:  # saraksts jau DESC pēc vote_date, vote_time
        total = ((v.get("total_par") or 0) + (v.get("total_pret") or 0)
                 + (v.get("total_atturas") or 0))
        title = (v.get("summary") or v.get("motif") or "").strip()
        if not v.get("result") or total == 0 or not title or title in seen:
            continue
        seen.add(title)
        out.append({
            "id": v["id"],
            "date": str(v.get("vote_date") or "")[:10],
            "title": title,
            "par": v.get("total_par") or 0,
            "pret": v.get("total_pret") or 0,
            "atturas": v.get("total_atturas") or 0,
            "result": v.get("result"),
        })
        if len(out) == limit:
            break
    return out


def hero_feed(
    db: sqlite3.Connection,
    hero_cards: list[dict[str, Any]],
    votes: list[dict[str, Any]],
    focus: dict[str, Any],
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Hero karuseļa jauktais saturs (spec 2026-07-07): ≤6 {kind, item} kartītes.

    Svaigās pretrunas (<_FRESH_DAYS) līdz 2; ja svaigu nav — 1 jaunākā kā
    enkurs. Pozīcijas nedublē kompozīta citātus. Round-robin mija sākas ar
    pretrunu; viena veida kartītes blakus nonāk tikai atlikumā.
    """
    cutoff = ((today or today_lv()) - timedelta(days=_FRESH_DAYS)).isoformat()
    fresh = [c for c in hero_cards if (c.get("detected_at") or "")[:10] >= cutoff]
    cons = fresh[:2] if fresh else hero_cards[:1]
    vote_items = _hero_votes(votes)
    pos_limit = min(3, 6 - len(cons) - len(vote_items))
    positions = _top_positions(db, _focus_used_urls(focus), pos_limit, today=today)
    queues = [("contradiction", list(cons)), ("position", positions), ("vote", vote_items)]
    items: list[dict[str, Any]] = []
    while len(items) < 6 and any(q for _, q in queues):
        for kind, q in queues:
            if q and len(items) < 6:
                items.append({"kind": kind, "item": q.pop(0)})
    return items
```

- [ ] **Step 2.2: Testi zaļi**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_focus.py -v`
Expected: PASS visi (arī vecie kompozīta testi)

- [ ] **Step 2.3: Commit**

```bash
git add src/render/focus.py tests/test_render_focus.py
git commit -m "feat(landing): hero_feed — jauktais hero karuseļa saturs (pretrunas+pozīcijas+balsojumi)"
```

### Task 3: dashboard vadojums + šablons

**Files:**
- Modify: `src/render/dashboard.py:39` (imports), `:342-346` (focus bloks), `:352` (konteksts)
- Modify: `templates/index.html.j2:28-69` (karuseļa bloks)

- [ ] **Step 3.1: `dashboard.py` — imports un `hero_items`**

Rinda 39:
```python
from src.render.focus import _hot_topic, _quote_of_day, assemble_focus, hero_feed
```

Aiz `focus = assemble_focus(...)` bloka (rindas ~344–346) pievieno:
```python
    # Hero karuselis: jauktais saturs (spec 2026-07-07) — pretrunas no
    # hero_cards, balsojumi no jau nofetčotā votes, pozīcijas dedupē pret
    # kompozīta citātiem.
    hero_items = hero_feed(db, hero_cards, votes, focus)
```

Kontekstā (rinda ~352) aizstāj `"hero_contradictions": hero_cards,` ar:
```python
        "hero_items": hero_items,
```

- [ ] **Step 3.2: `templates/index.html.j2` — karuseļa bloks**

Aizstāj rindas 28–69 (`{% if hero_contradictions %}` … `{% endif %}` ieskaitot dots bloku) ar:

```jinja
  {% if hero_items %}
  <div class="hero-feature" id="heroFeature">
    <div class="hero-feature-kicker"><span class="hero-v2-live-dot"></span> Uzmanības centrā</div>
    <div class="hero-feature-stage">
      {% for it in hero_items %}
      {% set c = it.item %}
      {% if it.kind == 'contradiction' %}
      <a class="hero-feature-card{% if loop.first %} is-active{% endif %}" href="pretrunas/{{ c.id }}.html" data-i="{{ loop.index0 }}">
        <div class="hero-feature-persona">
          {%- if c.has_photo %}
          <img class="hero-feature-avatar hero-feature-avatar-photo" src="assets/photos/{{ c.slug }}.jpg" alt="{{ c.politician_name }}" width="56" height="56" style="--pc: {{ c.party_color }}">
          {%- else %}
          <span class="hero-feature-avatar" style="--pc: {{ c.party_color }}">{{ c.initials }}</span>
          {%- endif %}
          <span class="hero-feature-persona-text">
            <span class="hero-feature-name">{{ c.politician_name }}</span>
            <span class="hero-feature-role">{{ c.party_short }}{% if c.topic %} · {{ c.topic }}{% endif %}</span>
          </span>
          <span class="hero-feature-badge">{{ c.severity_glyph }} {{ c.category_label or c.severity_lv }}{% if c.delta_days is not none %} · ΔT {{ c.delta_days }}d{% endif %}</span>
        </div>
        <div class="hero-feature-split">
          <div class="hero-feature-pane">
            <span class="hero-feature-pane-label">{{ c.old_label or 'Iepriekš' }} · {{ c.old_date }}</span>
            <span class="hero-feature-stance">{% if c.old_is_quote %}„{{ c.old_excerpt }}”{% else %}{{ c.old_excerpt }}{% endif %}</span>
          </div>
          <span class="hero-feature-arrow" aria-hidden="true">→</span>
          <div class="hero-feature-pane hero-feature-pane-new">
            <span class="hero-feature-pane-label">{{ c.new_label or 'Pašlaik' }} · {{ c.new_date }}</span>
            <span class="hero-feature-stance">{% if c.new_is_quote %}„{{ c.new_excerpt }}”{% else %}{{ c.new_excerpt }}{% endif %}</span>
          </div>
        </div>
        <span class="hero-feature-cta">Skatīt pretrunu →</span>
      </a>
      {% elif it.kind == 'position' %}
      <a class="hero-feature-card{% if loop.first %} is-active{% endif %}" href="politiki/{{ c.slug }}.html" data-i="{{ loop.index0 }}">
        <div class="hero-feature-persona">
          {%- if c.has_photo %}
          <img class="hero-feature-avatar hero-feature-avatar-photo" src="assets/photos/{{ c.slug }}.jpg" alt="{{ c.name }}" width="56" height="56" style="--pc: {{ c.party_color }}">
          {%- else %}
          <span class="hero-feature-avatar" style="--pc: {{ c.party_color }}">{{ c.initials }}</span>
          {%- endif %}
          <span class="hero-feature-persona-text">
            <span class="hero-feature-name">{{ c.name }}</span>
            <span class="hero-feature-role">{{ c.party_short }}{% if c.party_short and c.topic %} · {% endif %}{{ c.topic }}</span>
          </span>
          <span class="hero-feature-badge">Pozīcija</span>
        </div>
        <div class="hero-feature-pane">
          <span class="hero-feature-pane-label">{{ c.date }} · {{ c.source_domain }}</span>
          <span class="hero-feature-stance">„{{ c.quote }}”</span>
        </div>
        <span class="hero-feature-cta">Skatīt profilu →</span>
      </a>
      {% elif it.kind == 'vote' %}
      <a class="hero-feature-card{% if loop.first %} is-active{% endif %}" href="balsojumi.html#vote-{{ c.id }}" data-i="{{ loop.index0 }}">
        <div class="hero-feature-persona">
          <span class="hero-feature-persona-text">
            <span class="hero-feature-name">Saeimas balsojums</span>
            <span class="hero-feature-role">{{ c.date|lv_date }}</span>
          </span>
          <span class="hero-feature-badge">{{ c.result }}</span>
        </div>
        <div class="hero-feature-pane">
          <span class="hero-feature-stance">{{ c.title }}</span>
        </div>
        <div class="hero-vote-bar" role="img" aria-label="Par {{ c.par }}, pret {{ c.pret }}, atturas {{ c.atturas }}">
          <span class="hero-vote-par" style="flex-grow: {{ c.par }}"></span>
          <span class="hero-vote-pret" style="flex-grow: {{ c.pret }}"></span>
          <span class="hero-vote-att" style="flex-grow: {{ c.atturas }}"></span>
        </div>
        <div class="hero-vote-legend"><span>Par {{ c.par }}</span><span>Pret {{ c.pret }}</span><span>Atturas {{ c.atturas }}</span></div>
        <span class="hero-feature-cta">Skatīt balsojumu →</span>
      </a>
      {% endif %}
      {% endfor %}
    </div>
    {% if hero_items|length > 1 %}
    <div class="hero-feature-dots">
      {% for it in hero_items %}
      <button type="button" class="hero-feature-dot{% if loop.first %} is-active{% endif %}" data-i="{{ loop.index0 }}" aria-label="{{ {'contradiction': 'Pretruna', 'position': 'Pozīcija', 'vote': 'Balsojums'}[it.kind] }} {{ loop.index }}"></button>
      {% endfor %}
    </div>
    {% endif %}
  </div>
  {% endif %}
```

NB: pretrunu kartītes marķējums ir 1:1 esošais (nemainīts); JS bloks faila beigās (rindas ~640–669) paliek neaiztikts.

- [ ] **Step 3.3: Pārbaudi, ka `hero_contradictions` vairs nekur nav**

Run: `grep -rn "hero_contradictions" templates/ src/`
Expected: 0 rezultātu

- [ ] **Step 3.4: Šaurais renders bez kļūdām**

Run: `.venv/Scripts/python.exe -m src.render --only=dashboard`
Expected: exit 0; `output/atmina/index.html` satur `hero-feature-card` un vismaz vienu no `Skatīt profilu`/`Skatīt balsojumu` (dzīvajā DB ir gan pozīcijas, gan balsojumi)

- [ ] **Step 3.5: Commit**

```bash
git add src/render/dashboard.py templates/index.html.j2
git commit -m "feat(landing): hero karuselis rotē jauktu saturu — pretrunas, pozīcijas, balsojumi"
```

### Task 4: CSS — grid-stack augstums + balsojuma josla

**Files:**
- Modify: `assets/style.css:5710-5717` (stage/card), pievieno jaunus noteikumus aiz `.hero-feature-cta` bloka (~5746)

- [ ] **Step 4.1: Grid-stack (augstums nelēkā starp kartīšu veidiem)**

Aizstāj:
```css
.hero-feature-stage { position: relative; }
```
ar:
```css
.hero-feature-stage { display: grid; }
```

`.hero-feature-card` noteikumā aizstāj `display: none;` ar:
```css
  grid-area: 1 / 1; visibility: hidden;
```

Aizstāj:
```css
.hero-feature-card.is-active { display: block; animation: heroFeatureFade 0.5s ease; }
```
ar:
```css
.hero-feature-card.is-active { visibility: visible; animation: heroFeatureFade 0.5s ease; }
```

- [ ] **Step 4.2: Balsojuma josla (aiz `.hero-feature-card:hover .hero-feature-cta` noteikuma)**

```css
.hero-vote-bar {
  display: flex; gap: 2px; height: 8px; border-radius: 4px; overflow: hidden;
  margin-top: 0.7rem;
}
.hero-vote-par { background: var(--green); }
.hero-vote-pret { background: var(--red); }
.hero-vote-att { background: var(--yellow); }
.hero-vote-legend {
  display: flex; gap: 1rem; margin-top: 0.35rem;
  font-size: 0.72rem; color: var(--text-muted);
}
```

(`--green/--red/--yellow` jau eksistē — tos lieto `.badge-green/red/yellow`; joslas ir krāsu bloki, ne teksts, tāpēc light-theme AA teksta pārrakstes nav vajadzīgas.)

- [ ] **Step 4.3: Renders + vizuāla pārbaude**

Run: `.venv/Scripts/python.exe -m src.render --only=dashboard`
Tad Playwright (plugin) uz `output/atmina/index.html`: 1440px un 375px, gaišā UN tumšā tēma (`localStorage.setItem('theme','dark')` + reload). Pārbaudi:
- karuseļa augstums nemainās, klikšķinot punktus (garākā kartīte nosaka augstumu);
- balsojuma kartītē josla + leģenda salasāma abās tēmās;
- nav horizontālā scroll 375px.

- [ ] **Step 4.4: Commit**

```bash
git add assets/style.css
git commit -m "fix(landing): hero karuseļa grid-stack augstums + balsojuma joslas stils"
```

### Task 5: Baselines + pilnā verifikācija

**Files:**
- Modify: `tests/baselines/` (REGEN ceļā), iespējams `tests/fixtures/render_fixture_data.sql` nemainās

- [ ] **Step 5.1: Char-baseline REGEN (index.html apzināti mainīts)**

Run: `REGEN=1 .venv/Scripts/python.exe -m pytest tests/test_render_chars.py`
Expected: "Regenerated baseline" skip; tad bez REGEN:
Run: `.venv/Scripts/python.exe -m pytest tests/test_render_chars.py`
Expected: PASS

- [ ] **Step 5.2: Pilnais drošības tīkls**

Run: `bash scripts/check.sh`
Expected: ruff clean, pytest PASS, generate_public_site smoke OK

- [ ] **Step 5.3: Commit**

```bash
git add tests/
git commit -m "test(landing): hero karuseļa baselines regen pēc jauktā satura"
```

**Deploy NAV šī plāna daļa** — publish pause: operatora apstiprinājums pirms `deploy.sh --no-delete`.

---

## Self-review piezīmes

- Spec pārklājums: sastāva noteikumi (T1–T2), šablons ar 3 veidiem + dots aria (T3), grid-stack + josla (T4), REGEN + check.sh + Playwright abas tēmas (T4.3, T5). JS bez izmaiņām — nav taska.
- Tipu konsekvence: `hero_feed(db, hero_cards, votes, focus, today=None)` visur; vote item atslēgas `id/date/title/par/pret/atturas/result` sakrīt starp implementāciju (T2) un šablonu (T3).
- `lv_date` filtrs jau eksistē (to lieto `recent_votes` mini-tabula).
