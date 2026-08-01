# Uzmanības centra C slota steks — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kompozīta C slots kļūst par vertikālu steku — līdz 3 svaigas spriedzes + dienas citāts — tukšuma vietā zem īsā viena dueļa.

**Architecture:** `assemble_focus` atgriež `slot_c_items` sarakstu (`slot_c` vietā); `_fresh_tension` vispārinās uz `_fresh_tensions(tensions, limit, exclude)`. Šablonā B slots renderējas kā līdz šim, C slots — savs bloks ar ciklu. `_focus_used_urls` (hero dedup) pielāgojas jaunajai formai. `dashboard.py` NEMAINĀS (focus iet cauri nemainīts).

**Tech Stack:** Python 3 + Jinja2 + tīrs CSS; pytest hermētiskie testi.

**Spec:** `docs/superpowers/specs/2026-07-07-focus-c-slota-steks-design.md`

**Konteksts izpildītājam:** `src/render/focus.py` — landing "Uzmanības centrā" datu helperi. Pašreizējā `assemble_focus` (rindas ~159–190) liek vienu vienumu katrā no `slot_b`/`slot_c`; `_fresh_tension` (rindas ~150–156) atgriež vienu svaigāko. `_focus_used_urls` (rindas ~192–200) baro hero karuseļa pozīciju dedup — tā OBLIGĀTI jāpielāgo `slot_c_items` formai. Šablona C zars: `templates/index.html.j2` `{% for slot in [focus.slot_b, focus.slot_c] %}` konstrukcija (~229.–339. rinda).

---

### Task 1: testu pielāgošana + jaunie (failing)

**Files:**
- Modify: `tests/test_render_focus.py`

- [ ] **Step 1.1: Aizstāj `test_fresh_tension_filters_14d_window` ar saraksta versiju**

Atrodi un aizstāj visu funkciju `test_fresh_tension_filters_14d_window` ar:

```python
def test_fresh_tensions_filters_14d_window_and_limit():
    from src.render.focus import _fresh_tensions
    old = {"created_at": "2026-01-01 10:00:00"}
    new1 = {"created_at": "2026-07-06 10:00:00", "source_name": "A", "target_name": "B"}
    new2 = {"created_at": "2026-07-05 10:00:00", "source_name": "C", "target_name": "D"}
    assert _fresh_tensions([old], 3, today=date(2026, 7, 7)) == []
    assert _fresh_tensions([new1, new2, old], 3, today=date(2026, 7, 7)) == [new1, new2]
    assert _fresh_tensions([new1, new2], 1, today=date(2026, 7, 7)) == [new1]
    assert _fresh_tensions([new1, new2], 3, exclude=new1, today=date(2026, 7, 7)) == [new2]
```

- [ ] **Step 1.2: Pielāgo 4 esošos `assemble_focus` testus jaunajai formai**

Aizstāj `_kinds` helperi un 4 testus (no `def _kinds(focus):` līdz faila `test_assemble_quote_never_duplicates_hot_topic_quote` beigām; konstantes HOT/CON_FRESH/CON_OLD/TEN/QOD/TODAY paliek) ar:

```python
def _c_kinds(focus):
    return [s["kind"] for s in focus["slot_c_items"]]


def test_assemble_fresh_contradiction_then_c_stack():
    from src.render.focus import assemble_focus
    f = assemble_focus(HOT, [CON_FRESH, CON_OLD], [TEN], QOD, today=TODAY)
    assert f["slot_b"]["kind"] == "contradiction" and f["slot_b"]["item"]["id"] == 42
    assert _c_kinds(f) == ["tension", "quote"]  # citāts vienmēr pēdējais


def test_assemble_stale_contradiction_promotes_tension_to_b():
    from src.render.focus import assemble_focus
    f = assemble_focus(HOT, [CON_OLD], [TEN], QOD, today=TODAY)
    assert f["slot_b"]["kind"] == "tension"
    assert _c_kinds(f) == ["quote"]  # B spriedze neatkārtojas C stekā


def test_assemble_only_quote_goes_to_b():
    from src.render.focus import assemble_focus
    f = assemble_focus(HOT, [CON_OLD], [], QOD, today=TODAY)
    assert f["slot_b"]["kind"] == "quote"
    assert f["slot_c_items"] == []


def test_assemble_quote_never_duplicates_hot_topic_quote():
    from src.render.focus import assemble_focus
    dup = {"quote": "x", "source_url": "https://x.com/v/0"}  # jau A slotā
    f = assemble_focus(HOT, [CON_OLD], [], dup, today=TODAY)
    assert f["slot_b"] is None and f["slot_c_items"] == []


def test_assemble_c_stack_caps_three_tensions_quote_last():
    from src.render.focus import assemble_focus
    tensions = [
        {"created_at": f"2026-07-0{d} 10:00:00", "source_name": "A", "target_name": "B"}
        for d in (6, 5, 4, 3, 2)
    ]
    f = assemble_focus(HOT, [CON_FRESH], tensions, QOD, today=TODAY)
    assert _c_kinds(f) == ["tension", "tension", "tension", "quote"]
    assert [s["item"]["created_at"][:10] for s in f["slot_c_items"][:3]] == [
        "2026-07-06", "2026-07-05", "2026-07-04"]


def test_assemble_b_tension_excluded_from_c_stack():
    from src.render.focus import assemble_focus
    t1 = {"created_at": "2026-07-06 10:00:00", "source_name": "A", "target_name": "B"}
    t2 = {"created_at": "2026-07-05 10:00:00", "source_name": "C", "target_name": "D"}
    f = assemble_focus(HOT, [CON_OLD], [t1, t2], QOD, today=TODAY)
    assert f["slot_b"]["item"] is t1
    assert [s["item"] for s in f["slot_c_items"] if s["kind"] == "tension"] == [t2]


def test_focus_used_urls_reads_c_stack_quote():
    from src.render.focus import _focus_used_urls
    focus = {"hot": {"quotes": [{"source_url": "https://x.com/hot/1"}]},
             "slot_b": None,
             "slot_c_items": [
                 {"kind": "tension", "item": {"source_name": "A"}},
                 {"kind": "quote", "item": {"source_url": "https://x.com/q/9"}},
             ]}
    assert _focus_used_urls(focus) == {"https://x.com/hot/1", "https://x.com/q/9"}
```

NB: hero_feed testu bloks faila beigās (`EMPTY_FOCUS = {"hot": None, "slot_b": None, "slot_c": None}`) — aizstāj `"slot_c": None` ar `"slot_c_items": []`, un testā `test_hero_feed_position_skips_slot_quote_url` aizstāj `"slot_b": {...}, "slot_c": None` konstrukciju tā, lai citāts ir `slot_b` (paliek kā ir) — tikai `"slot_c": None` atslēga jāaizstāj ar `"slot_c_items": []`.

- [ ] **Step 1.3: Testi krīt pareizi**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_focus.py -q`
Expected: FAIL — `ImportError: cannot import name '_fresh_tensions'` un/vai `KeyError: 'slot_c_items'`

### Task 2: focus.py implementācija

**Files:**
- Modify: `src/render/focus.py` — `_fresh_tension` aizstāšana, `assemble_focus` pārrakstīšana, `_focus_used_urls` pielāgošana

- [ ] **Step 2.1: Aizstāj `_fresh_tension` ar `_fresh_tensions`**

```python
_C_TENSIONS_MAX = 3


def _fresh_tensions(
    tensions: list[dict[str, Any]],
    limit: int,
    exclude: Optional[dict[str, Any]] = None,
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Svaigās spriedzes <14d no jau nofetčotā saraksta (DESC pēc created_at)."""
    cutoff = ((today or today_lv()) - timedelta(days=_FRESH_DAYS)).isoformat()
    out: list[dict[str, Any]] = []
    for t in tensions:
        if t is exclude:
            continue
        if (t.get("created_at") or "")[:10] >= cutoff:
            out.append(t)
            if len(out) == limit:
                break
    return out
```

- [ ] **Step 2.2: Pārraksti `assemble_focus`**

```python
def assemble_focus(
    hot: Optional[dict[str, Any]],
    contradictions: list[dict[str, Any]],
    tensions: list[dict[str, Any]],
    quote_of_day: Optional[dict[str, Any]],
    today: Optional[date] = None,
) -> dict[str, Any]:
    """B = pretruna(<14d) → spriedze(<14d) → citāts (viens vienums);
    C = steks: līdz _C_TENSIONS_MAX svaigas spriedzes (bez B dubļa) + citāts pēdējais.

    `contradictions` = orchestratora jau padotais enriched saraksts (satur
    detected_at; DESC). Citāts nekad nedublē A slota citātu (source_url).
    """
    cutoff = ((today or today_lv()) - timedelta(days=_FRESH_DAYS)).isoformat()
    fresh_c = next(
        (c for c in contradictions if (c.get("detected_at") or "")[:10] >= cutoff), None
    )
    used_urls = {q.get("source_url") for q in (hot or {}).get("quotes", [])}
    qod = quote_of_day if (quote_of_day and quote_of_day.get("source_url") not in used_urls) else None

    slot_b = None
    b_tension = None
    if fresh_c:
        slot_b = {"kind": "contradiction", "item": fresh_c}
    else:
        b_candidates = _fresh_tensions(tensions, 1, today=today)
        if b_candidates:
            b_tension = b_candidates[0]
            slot_b = {"kind": "tension", "item": b_tension}
        elif qod:
            slot_b, qod = {"kind": "quote", "item": qod}, None

    slot_c_items = [
        {"kind": "tension", "item": t}
        for t in _fresh_tensions(tensions, _C_TENSIONS_MAX, exclude=b_tension, today=today)
    ]
    if qod:
        slot_c_items.append({"kind": "quote", "item": qod})
    return {"hot": hot, "slot_b": slot_b, "slot_c_items": slot_c_items}
```

- [ ] **Step 2.3: Pielāgo `_focus_used_urls`** (aizstāj slot ciklu):

```python
def _focus_used_urls(focus: Optional[dict[str, Any]]) -> set:
    """source_url kopa, ko kompozīts jau rāda (karstās tēmas citāti + citātu sloti)."""
    focus = focus or {}
    urls = {q.get("source_url") for q in ((focus.get("hot") or {}).get("quotes") or [])}
    for slot in [focus.get("slot_b"), *(focus.get("slot_c_items") or [])]:
        if slot and slot.get("kind") == "quote":
            urls.add(slot["item"].get("source_url"))
    urls.discard(None)
    return urls
```

- [ ] **Step 2.4: Testi zaļi**

Run: `.venv/Scripts/python.exe -m pytest tests/test_render_focus.py -q`
Expected: PASS visi

- [ ] **Step 2.5: Commit**

```bash
git add src/render/focus.py tests/test_render_focus.py
git commit -m "feat(landing): assemble_focus C slots kļūst par steku — spriedzes + dienas citāts"
```

### Task 3: šablons + CSS

**Files:**
- Modify: `templates/index.html.j2` (C slota zars, ~229.–339. rinda)
- Modify: `assets/style.css` (aiz `.focus-duel-meta` noteikuma, ~6133. rinda)

- [ ] **Step 3.1: Šablonā B slots viens, C slots — steks**

Aizstāj rindu `{% for slot in [focus.slot_b, focus.slot_c] %}` ar `{% for slot in [focus.slot_b] %}` (viss iekšējais 3 zaru markup paliek neaiztikts).

Aiz šī `{% endfor %}` (tūlīt pirms `focus-grid` noslēdzošā `</div>`) pievieno:

```jinja
    {% if focus.slot_c_items %}
    <div class="focus-slot">
      {% set c_tensions = focus.slot_c_items | selectattr('kind', 'equalto', 'tension') | list %}
      {% if c_tensions %}
      <div class="focus-kicker">⚡ Spriedzes</div>
      {% for s in c_tensions %}
      {% set t = s.item %}
      <article class="focus-duel">
        <div class="focus-duel-pair">
          <a class="focus-duel-name" href="politiki/{{ t.source_slug }}.html">{{ t.source_name }}</a>
          <span class="focus-duel-arrow" aria-hidden="true">⟶</span>
          <a class="focus-duel-name" href="politiki/{{ t.target_slug }}.html">{{ t.target_name }}</a>
        </div>
        <p class="focus-duel-desc">{{ t.description }}</p>
        <div class="focus-duel-meta">{{ t.date }} · {{ t.type_lv }}{% if t.topic %} · {{ t.topic }}{% endif %}</div>
      </article>
      {% endfor %}
      <a class="focus-cta" href="spriedzes.html">Visas spriedzes &rarr;</a>
      {% endif %}
      {% for s in focus.slot_c_items if s.kind == 'quote' %}
      <div class="focus-kicker focus-kicker-stacked">Dienas citāts</div>
      {{ focus_quote_card(s.item) }}
      {% endfor %}
    </div>
    {% endif %}
```

- [ ] **Step 3.2: CSS steka atdalītāji** (aiz `.focus-duel-meta` noteikuma):

```css
.focus-duel + .focus-duel { border-top: 1px solid var(--border-soft); padding-top: 12px; margin-top: 12px; }
.focus-kicker-stacked { margin-top: 14px; }
```

- [ ] **Step 3.3: Renders + pārbaude**

Run: `.venv/Scripts/python.exe -m src.render --only=dashboard`
Expected: exit 0; `output/atmina/index.html` satur `⚡ Spriedzes` kicker un ≥2 `focus-duel` C stekā (dzīvajā DB 8 svaigas spriedzes).

- [ ] **Step 3.4: Commit**

```bash
git add templates/index.html.j2 assets/style.css
git commit -m "feat(landing): C slota steks šablonā — spriedžu saraksts + dienas citāts"
```

### Task 4: baselines + pilnā verifikācija (kontrolieris veic Playwright)

- [ ] **Step 4.1:** `REGEN=1 .venv/Scripts/python.exe -m pytest tests/test_render_chars.py` → skip; tad bez REGEN → PASS
- [ ] **Step 4.2:** `bash scripts/check.sh` → viss zaļš
- [ ] **Step 4.3:** Commit `tests/fixtures/render_baseline_dashboard.json`
- [ ] **Step 4.4 (kontrolieris):** Playwright 1440/375 abas tēmas — C kolonna piepildīta, atdalītāji, nav horizontālā scroll; deploy TIKAI ar operatora apstiprinājumu

---

## Self-review piezīmes

- Spec pārklājums: sastāvs (T1–T2), `_focus_used_urls` integrācija (T2.3 + tests T1.2), šablons+CSS (T3), verifikācija (T4). `dashboard.py` apzināti neskarts.
- Tipu konsekvence: `slot_c_items` = `list[{"kind","item"}]` visur; `_fresh_tensions(tensions, limit, exclude=None, today=None)` signatūra sakrīt testos un implementācijā.
- Vecais `_fresh_tension` (vienskaitlis) tiek AIZSTĀTS — pēc Task 2 `grep -n "_fresh_tension\b" src/ tests/` jādod 0 (tikai `_fresh_tensions`).
