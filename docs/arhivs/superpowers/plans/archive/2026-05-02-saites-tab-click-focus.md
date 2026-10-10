# Saites tab — klikšķis = fokus uz kartiņu (B-lite) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pārveidot individuālā politiķa profila Saites tabā mini-grafa mezgla klikšķi no tūlītējas teleportēšanas uz cita politiķa profilu par scroll-on-anchor uz attiecīgo kartiņu zem grafa, ar nulle JavaScript.

**Architecture:** Backend (`_fetch_saites_for_profile`) anotē katras saites kartiņas dictā `is_anchor` / `other_pid` / `other_slug`, virzot pirmo kartiņu pārim caur secību Uzbrukumi → Spriedzes → Atbalsts. Template pārsnaidz mezgla `<a xlink:href>` uz `#saites-{pid}` un anotētajām kartiņām pievieno `id="saites-{pid}"` + "Skatīt profilu →" pogu. CSS `.saites-card-anchor:target` flash animācija dod vizuālu apstiprinājumu. Native browser `:target` + smooth-scroll dara visu darbu.

**Tech Stack:** Python 3.11+ / pytest, Jinja2 templates, vanilla CSS (`assets/style.css`), SVG.

**Spec:** `docs/superpowers/specs/2026-05-02-saites-tab-click-focus-design.md`

---

## File Structure

**Modify:**
- `src/render/politicians.py` — `_fetch_saites_for_profile` (lines 220–287): per-card anotācijas pirms return
- `templates/politician.html.j2` — mini-grafa mezgli (lines 449–454) un trīs saites sekcijas (lines 458–507)
- `assets/style.css` — pievieno `:target` flash + node label + focus ring (~rinda 1840, aiz eksistējošā saites bloka)
- `tests/test_render_saites.py` — JAUNS: unit tests par `_fetch_saites_for_profile` anotāciju

**Touchpoint scope:**
- Funkcijas signatūra `_fetch_saites_for_profile(db, pid, profile_kind, tensions, commentary_about)` paliek nemainīga.
- Atgriezamā dict struktūra paplašinās: `uzbrukumi[i]` / `spriedzes[i]` / `atbalsts[i]` katrs ieguva trīs jaunas atslēgas.
- `commentary_about`, `vote_alignment_*`, `mini_graph` paliek nemainīgi.

---

### Task 1: Backend anotācija — testi un implementācija

**Files:**
- Test: `tests/test_render_saites.py` (jauns)
- Modify: `src/render/politicians.py:220–287`

- [ ] **Step 1: Pārbaudi pašreizējo `_fetch_saites_for_profile` signatūru un atgriezamo dict struktūru**

Atver `src/render/politicians.py` un izlasa funkciju `_fetch_saites_for_profile` (rindas 220–287). Pārbaudi, ka:
- Funkcija pieņem `(db, pid, profile_kind, tensions, commentary_about)`
- Atgriež dict ar `uzbrukumi`, `spriedzes`, `atbalsts`, `commentary_about`, `vote_alignment_top`, `vote_alignment_bottom`, `mini_graph`
- Pirms šī taska — kartiņu dicti satur tikai oriģinālo tension dict laukus (no `tension_rows`), bez papildu anotācijām

Tas nodod kontekstu jaunajām testa expectations.

- [ ] **Step 2: Uzraksti failed unit testu jaunam anotācijas uzvedībai**

Izveido `tests/test_render_saites.py` ar šādu saturu:

```python
"""Tests for _fetch_saites_for_profile per-card anchor annotation.

Spec: docs/superpowers/specs/2026-05-02-saites-tab-click-focus-design.md
"""

import sqlite3
import pytest

from src.render.politicians import _fetch_saites_for_profile


@pytest.fixture
def empty_db():
    """In-memory DB with row_factory — _fetch_saites_for_profile uses _vote_alignment_for
    only for profile_kind='deputy', so non-deputy profiles need no schema."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    return db


def _make_tension(source_pid, target_pid, tension_type, source_name="A", target_name="B",
                  source_party="JV", target_party="NA", topic="Drošība", description="...",
                  created_at="2026-04-30"):
    return {
        "source_pid": source_pid,
        "target_pid": target_pid,
        "tension_type": tension_type,
        "source_name": source_name,
        "target_name": target_name,
        "source_party": source_party,
        "target_party": target_party,
        "topic": topic,
        "description": description,
        "created_at": created_at,
    }


def test_first_card_for_pair_is_anchor(empty_db):
    """Single tension → its card is the anchor."""
    tensions = [_make_tension(1, 2, "uzbrukums")]
    out = _fetch_saites_for_profile(empty_db, pid=1, profile_kind="politician",
                                     tensions=tensions, commentary_about=[])
    assert out["uzbrukumi"][0]["is_anchor"] is True
    assert out["uzbrukumi"][0]["other_pid"] == 2
    assert out["uzbrukumi"][0]["other_slug"] == "b"


def test_second_card_same_pair_is_not_anchor(empty_db):
    """Same pair appears in uzbrukumi AND spriedzes — only uzbrukumi gets is_anchor."""
    tensions = [
        _make_tension(1, 2, "uzbrukums"),
        _make_tension(1, 2, "spriedze"),
    ]
    out = _fetch_saites_for_profile(empty_db, pid=1, profile_kind="politician",
                                     tensions=tensions, commentary_about=[])
    assert out["uzbrukumi"][0]["is_anchor"] is True
    assert out["spriedzes"][0]["is_anchor"] is False
    assert out["spriedzes"][0]["other_pid"] == 2  # still annotated, just not anchor


def test_anchor_walks_uzbrukumi_then_spriedzes_then_atbalsts(empty_db):
    """Same pair in atbalsts only → atbalsts card is anchor."""
    tensions = [_make_tension(1, 2, "atbalsts")]
    out = _fetch_saites_for_profile(empty_db, pid=1, profile_kind="politician",
                                     tensions=tensions, commentary_about=[])
    assert out["atbalsts"][0]["is_anchor"] is True


def test_other_pid_when_current_is_target(empty_db):
    """When the current politician is target_pid, other_pid is source_pid."""
    tensions = [_make_tension(2, 1, "uzbrukums", source_name="X", target_name="Y")]
    out = _fetch_saites_for_profile(empty_db, pid=1, profile_kind="politician",
                                     tensions=tensions, commentary_about=[])
    assert out["uzbrukumi"][0]["other_pid"] == 2
    assert out["uzbrukumi"][0]["other_slug"] == "x"


def test_two_distinct_pairs_both_anchors(empty_db):
    """Different other_pids → both cards anchored."""
    tensions = [
        _make_tension(1, 2, "uzbrukums"),
        _make_tension(1, 3, "uzbrukums", target_name="C"),
    ]
    out = _fetch_saites_for_profile(empty_db, pid=1, profile_kind="politician",
                                     tensions=tensions, commentary_about=[])
    assert out["uzbrukumi"][0]["is_anchor"] is True
    assert out["uzbrukumi"][1]["is_anchor"] is True
    assert out["uzbrukumi"][0]["other_pid"] == 2
    assert out["uzbrukumi"][1]["other_pid"] == 3


def test_empty_tensions_no_annotation_keys_in_empty_lists(empty_db):
    """No tensions → uzbrukumi/spriedzes/atbalsts are empty lists. No crash."""
    out = _fetch_saites_for_profile(empty_db, pid=1, profile_kind="politician",
                                     tensions=[], commentary_about=[])
    assert out["uzbrukumi"] == []
    assert out["spriedzes"] == []
    assert out["atbalsts"] == []


def test_diacritic_name_slugified(empty_db):
    """Latvian diacritics in target name → slug stripped."""
    tensions = [_make_tension(1, 2, "uzbrukums", target_name="Āris Šķērslis")]
    out = _fetch_saites_for_profile(empty_db, pid=1, profile_kind="politician",
                                     tensions=tensions, commentary_about=[])
    assert out["uzbrukumi"][0]["other_slug"] == "aris-skerslis"
```

- [ ] **Step 3: Palaid testus, lai verificētu, ka tie fail**

Komandrindas:

```bash
.venv/Scripts/activate
python -m pytest tests/test_render_saites.py -v
```

Sagaidāmais: visi 7 testi FAIL ar `KeyError: 'is_anchor'` (vai līdzīgi), jo anotācija vēl nav pievienota.

- [ ] **Step 4: Pievieno anotācijas helper funkciju un piemēro to katrai sekcijai**

Failā `src/render/politicians.py`, funkcijā `_fetch_saites_for_profile` (sākas rindā ~220), tieši pirms esošās rindas `# Build mini-graf neighbors: up to 8 unique tension partners.` (rinda ~253), ievieto šādu anotācijas bloku:

```python
    # Anotē katras kartiņas other_pid / other_slug / is_anchor priekš
    # B-lite saites tab — pirmā kartiņa pārim (Uzbrukumi → Spriedzes → Atbalsts)
    # saņem is_anchor=True, kalpojot kā URL fragment target.
    anchored_pids: set[int] = set()

    def _annotate_card(t: dict[str, Any]) -> dict[str, Any]:
        if t.get("source_pid") == pid:
            other_pid = t.get("target_pid")
            other_name = t.get("target_name")
        else:
            other_pid = t.get("source_pid")
            other_name = t.get("source_name")
        is_anchor = other_pid is not None and other_pid not in anchored_pids
        if is_anchor:
            anchored_pids.add(other_pid)
        return {
            **t,
            "other_pid": other_pid,
            "other_slug": _slugify(other_name) if other_name else "",
            "is_anchor": is_anchor,
        }

    uzbrukumi = [_annotate_card(t) for t in uzbrukumi]
    spriedzes = [_annotate_card(t) for t in spriedzes]
    atbalsts = [_annotate_card(t) for t in atbalsts]
```

Apstiprini, ka `_slugify` jau ir importēts no `src.render._common` (rinda 17–23 file augšpusē — jāpārbauda; ja nē, tas jāpievieno).

- [ ] **Step 5: Palaid testus, lai verificētu, ka tie passē**

```bash
python -m pytest tests/test_render_saites.py -v
```

Sagaidāmais: visi 7 testi PASS.

- [ ] **Step 6: Palaid pilno test suite, lai verificētu nekādu regresiju**

```bash
bash scripts/check.sh
```

Sagaidāmais: ruff clean, pytest visi tests pass, generate_public_site smoke OK.

- [ ] **Step 7: Commit**

```bash
git add tests/test_render_saites.py src/render/politicians.py
git commit -F .git-commit-msg.tmp
```

Iepriekš `.git-commit-msg.tmp` saturs:

```
feat(politicians): annotate saites cards with is_anchor + other_pid/slug

For B-lite saites tab redesign — first card per pair (walking Uzbrukumi
→ Spriedzes → Atbalsts) is the anchor target for #saites-{pid} fragment
links from the mini-graph. other_slug enables "Skatīt profilu →" buttons
on every card.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

(Ja .git-commit-msg.tmp fails atstājies no spec commit'a, sākotnēji `Remove-Item .git-commit-msg.tmp` PowerShell vai `rm` Bash.)

---

### Task 2: Markup — mini-grafa mezgli (anchor href + name label)

**Files:**
- Modify: `templates/politician.html.j2:449–454`

- [ ] **Step 1: Atver template un atrod mini-grafa mezgla bloku**

Failā `templates/politician.html.j2`, atrod sekciju (rindas 437–456), kas sākas ar `{% if saites_data.mini_graph.neighbors %}` un satur mezglu `<a xlink:href="../politiki/{{ n.slug }}.html">` (rinda 450).

- [ ] **Step 2: Pārveido neighbor mezgla `<a>` href + pievieno vārda etiķeti**

Aizvieto rindas 449–454 (`{% for n in saites_data.mini_graph.neighbors %}` ... `{% endfor %}` neighbor render bloks) ar:

```html
      {# Neighbors — klikšķis aizved uz attiecīgo saites kartiņu zem grafa, ne uz cita profila lapu (B-lite). #}
      {% for n in saites_data.mini_graph.neighbors %}
      <a xlink:href="#saites-{{ n.pid }}" aria-label="{{ n.name }} ({{ n.tension_type }}) — skatīt detaļas">
        <circle cx="{{ n.x }}" cy="{{ n.y }}" r="9" fill="{{ n.party_color }}" stroke="#fff" stroke-width="1.5"/>
        <title>{{ n.name }} ({{ n.tension_type }})</title>
      </a>
      <text x="{{ n.x }}" y="{{ n.y + 22 }}" text-anchor="middle" font-size="9"
            fill="var(--text-muted)" class="saites-node-label">{{ n.name.split()[0] }}</text>
      {% endfor %}
```

Atšķirības no oriģināla:
- `xlink:href` no `../politiki/{{ n.slug }}.html` → `#saites-{{ n.pid }}`
- Pievienots `aria-label` uz `<a>`
- Pievienots `<text>` etiķete zem mezgla ar pirmo vārdu (kā centra mezgls jau dara rindā 447)

- [ ] **Step 3: Render lapu un manuāli pārbaudi mezgla atribūtus**

```bash
python -c "from src.render import generate_public_site; generate_public_site()"
```

Atver kāda politiķa profila HTML failu izvades direktorijā (piem., `output/atmina/politiki/lato-lapsa.html`) un meklē mini-grafa SVG. Pārbaudi:
- Mezglu `<a xlink:href="#saites-...">` (nevis `../politiki/...html`)
- Zem katra mezgla `<text class="saites-node-label">{vārds}</text>`
- Mezgls joprojām ir click-focusable (`<a>` saglabāts)

- [ ] **Step 4: Pārbaudi tests joprojām passē (template render smoke)**

```bash
bash scripts/check.sh
```

Sagaidāmais: viss pass.

- [ ] **Step 5: Commit**

`.git-commit-msg.tmp` saturs:

```
feat(politician-template): mini-graph node anchors + visible name labels

Mezgla klikšķis vairs nav teleports — href = #saites-{pid} fragment.
Vārda etiķete (pirmais vārds) zem apļa, lai lietotājs redz, kurš ir kurš
pirms klikšķēšanas.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add templates/politician.html.j2
git commit -F .git-commit-msg.tmp
```

---

### Task 3: Markup — saites kartiņu anchor id + "Skatīt profilu" poga

**Files:**
- Modify: `templates/politician.html.j2:458–507` (3 sekcijas: Uzbrukumi, Spriedzes, Atbalsts)

- [ ] **Step 1: Pārveido Uzbrukumi sekcijas kartiņu**

Failā `templates/politician.html.j2`, atrod Uzbrukumi sekcijas `{% for t in saites_data.uzbrukumi %}` bloku (rindas 461–471). Aizvieto rindu 462 un pievieno profila pogu:

Pirms (rinda 462):

```html
      <div class="card" style="margin-bottom:0.5rem;">
```

Pēc:

```html
      <div class="card saites-card{% if t.is_anchor %} saites-card-anchor{% endif %}"
           {% if t.is_anchor %}id="saites-{{ t.other_pid }}"{% endif %}
           style="margin-bottom:0.5rem;">
```

Un rindas 469 (esošais avota links) aizvieto ar:

Pirms (rinda 469):

```html
        {% if t.source_url %}<a href="{{ t.source_url | safe_url }}" target="_blank" rel="noopener" style="font-size:0.8rem;">Avots ↗</a>{% endif %}
```

Pēc:

```html
        {% if t.source_url %}<a href="{{ t.source_url | safe_url }}" target="_blank" rel="noopener" style="font-size:0.8rem;">Avots ↗</a>{% endif %}
        {% if t.other_slug %}<a href="../politiki/{{ t.other_slug }}.html" class="saites-card-profile-btn" style="font-size:0.8rem; margin-left:0.5rem;">Skatīt profilu →</a>{% endif %}
```

- [ ] **Step 2: Pārveido Spriedzes sekciju (tas pats pattern)**

Atrod Spriedzes sekcijas `{% for t in saites_data.spriedzes %}` bloku (rindas 478–488). Veic identiskas izmaiņas:
- Aizvieto `<div class="card" style="margin-bottom:0.5rem;">` ar tādu pašu klašu+id rindu (skat. Step 1)
- Aiz `Avots ↗` saites pievieno `Skatīt profilu →` pogu (skat. Step 1)

- [ ] **Step 3: Pārveido Atbalsts sekciju (tas pats pattern)**

Atrod Atbalsts sekcijas `{% for t in saites_data.atbalsts %}` bloku (rindas 495–505). Identiskas izmaiņas (klase+id, profila poga).

- [ ] **Step 4: Render lapu un pārbaudi DOM**

```bash
python -c "from src.render import generate_public_site; generate_public_site()"
```

Atver politiķa profila HTML, pārbaudi:
- Vismaz vienai kartiņai katrā sekcijā ir `id="saites-{pid}"` (anchor)
- Tā pati kartiņa ir ar `class="card saites-card saites-card-anchor"`
- Citām (ja viens un tas pats other_pid) — `class="card saites-card"` bez `saites-card-anchor` un bez id
- Visās kartiņās blakus `Avots ↗` parādās `Skatīt profilu →` ar `href="../politiki/{slug}.html"`

- [ ] **Step 5: Manuāli pārbaudi anchor scroll plūsmu**

```bash
python serve.py
```

Atver `http://127.0.0.1:8080/atmina/politiki/{kāda-politiķa}.html` ar saites datiem. Pārslēdz uz Saites tabu. Klikšķī uz neighbor mezgla. Sagaidāmais: URL kļūst `#saites-{pid}`, lapa scrollē uz attiecīgo kartiņu. Animācija/highlight vēl nav (Task 4); šobrīd pārbauda tikai scroll.

- [ ] **Step 6: Pārbaudi tests un commit**

```bash
bash scripts/check.sh
```

Visi tests pass. `.git-commit-msg.tmp`:

```
feat(politician-template): saites cards anchor id + skatīt profilu pogas

Pirmā kartiņa pārim (caur Uzbrukumi → Spriedzes → Atbalsts) saņem
id="saites-{pid}" un saites-card-anchor klasi. Katrai kartiņai pievieno
"Skatīt profilu →" pogu uz cita politiķa lapu.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add templates/politician.html.j2
git commit -F .git-commit-msg.tmp
```

---

### Task 4: CSS — `:target` flash highlight + node label + focus ring

**Files:**
- Modify: `assets/style.css` (~rinda 1840, aiz eksistējošā saites bloka)

- [ ] **Step 1: Atrod eksistējošo saites CSS bloku**

Failā `assets/style.css`, atrod rindas 1810–1836 — `.mini-saites-graph`, `.saites-link-*`, `.saites-section*` deklarācijas. Jaunais bloks tiks pievienots tieši aiz `.alignment-list` (~rinda 1837).

- [ ] **Step 2: Pievieno B-lite CSS bloku**

Pievieno aiz `.alignment-list li:last-child { border-bottom: none; }` (rinda 1836):

```css

/* Saites tab — B-lite anchor highlight + node labels (spec 2026-05-02) */
.saites-card-anchor:target {
  animation: saites-card-flash 2s ease-out;
  scroll-margin-top: 80px; /* under sticky .nav (assets/style.css:82) */
}

@keyframes saites-card-flash {
  0%   { background-color: rgba(255, 215, 0, 0.18); box-shadow: 0 0 0 2px rgba(255, 215, 0, 0.35); }
  100% { background-color: transparent;            box-shadow: 0 0 0 0 transparent; }
}

@media (prefers-reduced-motion: reduce) {
  .saites-card-anchor:target {
    animation: none;
    background-color: rgba(255, 215, 0, 0.10);
  }
}

.saites-node-label { pointer-events: none; user-select: none; }
.mini-saites-graph a { cursor: pointer; }
.mini-saites-graph a:hover circle { stroke-width: 2.5; }
.mini-saites-graph a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
```

- [ ] **Step 3: Render lapu un manuāli verificē animāciju**

```bash
python -c "from src.render import generate_public_site; generate_public_site()"
python serve.py
```

Atver `http://127.0.0.1:8080/atmina/politiki/{politiķa ar saitēm}.html`. Pārslēdz uz Saites tabu. Klikšķi uz neighbor mezgla:
- Lapa smooth-scrollē uz attiecīgo kartiņu
- Kartiņa ~2 sekundes ar zeltainu fonu, tad nopludinās līdz caurspīdīgam
- Kartiņa NEIET zem sticky nav joslas (scroll-margin)

Pārbaudi `:focus-visible`: Tab uz mini-grafu, redzams accent kontūra ap fokusēto mezglu.

Pārbaudi `prefers-reduced-motion`: Chrome DevTools → Rendering → "Emulate CSS prefers-reduced-motion: reduce" → klikšķi mezglu → nav animācijas, tikai statisks gaišs fons.

- [ ] **Step 4: Pārbaudi tests + render smoke**

```bash
bash scripts/check.sh
```

Sagaidāmais: viss pass.

- [ ] **Step 5: Commit**

`.git-commit-msg.tmp`:

```
feat(style): saites card flash on :target + node label + focus ring

CSS pievieno B-lite vizuālo atgriezenisko saiti — kartiņa ~2s zeltaini
mirgo pēc anchor-scroll, mezglu vārdu etiķetes nav klikšķamas, mini-grafa
mezgliem accent focus-visible kontūra. prefers-reduced-motion fallback uz
statisku highlight.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

```bash
git add assets/style.css
git commit -F .git-commit-msg.tmp
```

---

### Task 5: End-to-end manuālā verifikācija + edge cases

**Files:** none (verifikācija)

- [ ] **Step 1: Pilna verifikācija ar realdatu profilu**

```bash
python -c "from src.render import generate_public_site; generate_public_site()"
python serve.py
```

Atver Lato Lapsa profilu (tā ir spec piemērs ar 6+ saitēm): `http://127.0.0.1:8080/atmina/politiki/lato-lapsa.html`. Pārslēdz uz Saites tabu. Pārbaudi:
- [ ] Mezgliem zem apļiem redzami pirmie vārdi
- [ ] Klikšķis uz mezgla → URL `#saites-{pid}` → scroll uz kartiņu
- [ ] Kartiņa zelta-flash ~2s
- [ ] Kartiņā ir "Skatīt profilu →" poga, kas iet uz `politiki/{slug}.html`
- [ ] Klikšķis uz pogas → tagad navigē uz to profilu
- [ ] Browser back-button atgriež uz iepriekšējo anchor stāvokli

- [ ] **Step 2: Klaviatūras nav pārbaude**

Tajā pašā lapā:
- Tab līdz mini-grafa pirmajam mezglam — `:focus-visible` accent kontūra
- Enter — anchor scroll + flash
- Tab vēl tālāk — nākamais mezgls, atkārto

- [ ] **Step 3: Mobile responsive pārbaude**

DevTools → Toggle device toolbar → 375×812 (iPhone SE). Tajā pašā lapā:
- [ ] Mezglu vārdi joprojām redzami
- [ ] Tap uz mezgla scrollē uz kartiņu
- [ ] Kartiņa flash strādā
- [ ] "Skatīt profilu →" poga ir tap-friendly

- [ ] **Step 4: Reduced-motion pārbaude**

DevTools → Rendering panel → "Emulate CSS prefers-reduced-motion: reduce". Klikšķi mezglu. Sagaidāmais: nav animācijas, kartiņai paliek statiski gaišs fons (rgba 0.10), bet skaidri redzams kura kartiņa atlasīta.

- [ ] **Step 5: Edge case — profila bez saites tab**

Atver politiķa profilu BEZ saites datiem (piem., bezdarbu žurnālistu). Sagaidāmais: Saites tabs vai nu nav redzams (`has_saites_content=False`), vai parāda "Nav saišu datu." (eksistējošais guard rindā 551). Mini-grafa nav, anchor scroll nav iespējams — nav jāstrādā.

- [ ] **Step 6: Edge case — viens un tas pats pid vairākās kategorijās**

Atrod profila piemēru, kur viens cits politiķis parādās gan `uzbrukumi`, gan `spriedzes` sarakstos. Klikšķi mezglu. Sagaidāmais: scroll iet uz Uzbrukumi kartiņu (pirmā secībā), spriedze kartiņa redzama tieši zem.

- [ ] **Step 7: Atkārtots klikšķis uz tā paša mezgla**

Klikšķi neighbor mezglu (kartiņa flash). Klikšķi to pašu mezglu vēlreiz. Sagaidāmais: nekas nemainās (URL fragment jau atbilst, browser neaktivē `:target` no jauna). Tas ir spec atklāti documented edge case (skat. spec § Riski un nezināmie).

- [ ] **Step 8: Final smoke + commit (jākoriģē, ja kaut kas)**

```bash
bash scripts/check.sh
```

Ja Step 1–7 kāda daļa neatbilst sagaidāmajam, atgriezies pie atbilstošās task'as un labo. Ja viss OK — nav jaunu izmaiņu, tāpēc nav jauna commit'a; manuālā verifikācija ir reģistrēta uzrakstā šajā plānā.

---

## Self-Review

**Spec coverage:**
- Spec § Backend delta (other_pid/other_slug/is_anchor) → Task 1 ✓
- Spec § Markup delta (mini-grafa mezgli, anchor href + label) → Task 2 ✓
- Spec § Markup delta (saites kartiņu anchor id + Skatīt profilu poga, 3 sekcijas) → Task 3 ✓
- Spec § CSS delta (:target flash, node label, focus ring, prefers-reduced-motion) → Task 4 ✓
- Spec § Verifikācija (8 punkti — render, manuāls profilā, edge cases, klaviatūra, mobile, reduced motion) → Task 5 ✓
- Spec § Pieejamība (aria-label, focus-visible) → Task 2 (aria-label) + Task 4 (focus-visible) ✓

**Placeholder scan:** Nav TBD/TODO/"līdzīgi kā Task N" atsauču. Katrai code izmaiņai ir konkrēts diff.

**Type consistency:** `is_anchor` (bool), `other_pid` (int|None), `other_slug` (str) — viena un tā pati shēma izmantota Task 1 testos, implementācijā un Task 3 templātā. CSS klases `saites-card`, `saites-card-anchor`, `saites-node-label`, `saites-card-profile-btn` — visas konsistenti minētas Task 3 (radīšana templātā) un Task 4 (stili).

**Sticky header constant:** `scroll-margin-top: 80px` Task 4 atsaucas uz `assets/style.css:82` — pārbaudīts brainstorming kontekstā (sticky `.nav` ir ~60–80px atkarībā no viewport).
