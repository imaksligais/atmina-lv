# Plan: Role-aware profila tabu refactor

> **Datums:** 2026-05-01 · **Branch:** `feat/profile-roles` · **Worktree:** `.worktrees/profile-roles`
> **Design sesija:** 2026-05-01 Telegram (Elviss ↔ Claude Opus 4.7) · **Execute:** jauna sesija
> **Estimate:** ~165 līniju jauna koda + ~30 dzēstas (X+Ziņas merge) = neto ~140 līniju · ~3h ar testiem

---

## 0. Sesijas sākums (jaunajai sesijai)

```bash
# Pārliecinies, ka esi worktree, ne master
cd "~/atmina/.worktrees/profile-roles"
git rev-parse --abbrev-ref HEAD   # MUST output: feat/profile-roles
git status                         # Pārbaudi tīru working tree
.venv/Scripts/activate
```

Lasi vispirms:
- `wiki/index.md` — projekta stāvokļa overview
- `CLAUDE.md` — datu kontrakti, pipeline invariants, koalīcijas klasifikācija
- `wiki/CHANGELOG.md` § F3a-F3g (~16 ieraksti) — render moduļa F4 leaf rule precedents
- `src/coalition.py` — arhitektūras precedents jaunajam modulim (75 līniju, ar docstring un 2 funkcijām)
- `src/render/politicians.py:1-35` — politicians.py docstring saka "Imports flow strictly from `src.render._common` — no peer-module dependencies"
- `tests/test_render_chars.py` (REGEN konvencija) un commit `c9c80ea` (REGEN piemērs)

---

## 1. Konteksts

### Problem statement

Pašreizējais `politiki/<slug>.html` profils rāda līdz 9 tabu (Laika līnija, Pozīcijas, Pretrunas, Komentāri, Balsojumi, Spriedzes, X, Ziņas, Likumprojekti). Reālas problēmas:

1. **Žurnālistiem rādās tukšs "Pozīcijas" tab** — viņiem nav first-party pozīciju, tikai komentāri par citiem
2. **Ministrēm un PM rādās "Balsojumi" tab** — bet viņi parasti nebalso (Siliņa, Braže, Sprūds — visi 0 votes)
3. **"Spriedzes" stat-poga lumping** — counts visas tensions (uzbrukumi + spriedzes + atbalsts) zem viena. Pirms #90 dzēšanas Šleseram rādīja "2 Spriedzes", lai gan tikai 1 bija type='spriedze'.
4. **9 tabu kognitīvā slodze** — daudz dublicējas konceptuāli (X+Ziņas+Pozīcijas = "ko saka")

### Lietotāja konkrētās izvēles (Telegram 2026-05-01)

| Jautājums | Atbilde |
|---|---|
| (a) Multi-role: Siliņa = deputāte vai PM? | Vienmēr `minister`. Ministrs nekad NAV `deputy`, pat ja mandāts |
| (b) Bijušajiem rādīt vēsturisko Saeimā tab? | Jā, ar "vēsturisks" marker |
| (c) Saites tab struktūra | Variants 2: mini-graf (~250px) + 3 type-color sekcijas + linka uz pilno /saites.html |
| (d) Organizācijas split | Datu-driven; LDDK rāda Pozīciju tab, Saeimas ziņas — ne. Schema split nav vajadzīgs |

### Apstiprinātais profile_kind kopums

10 vērtības: `deputy`, `minister`, `mep`, `regional`, `politician`, `journalist`, `analyst`, `organization`, `former`, `inactive`.

### Tabu mapping pa profile_kind

| Tabs | deputy | minister | mep | regional | politician | journalist | analyst | organization | former |
|---|---|---|---|---|---|---|---|---|---|
| Laika līnija | ✅ default | ✅ default | ✅ default | ✅ default | ✅ default | ✅ default | ✅ default | ✅ default | ✅ default |
| Pozīcijas | ✅ | ✅ | ✅ | ✅ | ✅ | – | – | ✅ | ✅ |
| Saeimā (votes+bills) | ✅ | – | – | – | – | – | – | – | (vēsturiski) |
| Komentāri-by (kuru komentē) | – | – | – | – | – | ✅ | ✅ | – | – |
| Publikācijas (X + ziņas merged) | (zem Pozīcijas) | (zem Pozīcijas) | (zem Pozīcijas) | (zem Pozīcijas) | (zem Pozīcijas) | ✅ | ✅ | – | (zem Pozīcijas) |
| Pretrunas | ✅ | ✅ | ✅ | ✅ | ✅ | (ja >0) | (ja >0) | ✅ | ✅ |
| Saites | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (ja >0) | ✅ (ja >0) | ✅ | ✅ |

Rezultāts: 5 tabi deputātam, 4 ministrām/MEP/regional/politician, 3 žurnālistam/analītiķim, 3 organizācijai.

---

## 2. Arhitektūras alignment review (3 must-fix no design sesijas)

### MUST-FIX 1: Modulis kā `src/coalition.py` precedents

**Problēma:** Sākotnējais "30 līnijas inline politicians.py" pārkāpa projektā iedibināto pattern. `src/coalition.py` ir tieši šāds gadījums (75 līniju domain logic ar tipa Literal + funkciju + bagāts docstring).

**Pareizais placement:**
- `src/profile_kind.py` (~60 līniju, mirror coalition.py struktūru)
- `tests/test_profile_kind.py` (~25 līniju)
- `src/render/_common.py` re-eksportē `derive_profile_kind` (1 jauna importa rinda + 1 `__all__` rinda) — F4 leaf rule

### MUST-FIX 2: Char-fixture REGEN ir mandatory pēc F2

**Problēma:** Mans plāns nepieminēja REGEN. Bet wiki CHANGELOG 2026-04-30 (drift catch) padara to par eksplicītu daily routine soli, un mainās ~150 politiķu HTML hashes.

**Risinājums:** Atsevišķs commit `test(render): regen politicians baseline for role-aware tabs` PIRMS F3 polish. Konvencija: skat. recent commits `c9c80ea`, `83a4f51`.

### MUST-FIX 3: Derivation algoritma bug

**Problēma:** Reāls DB role-string: `"Saeimas deputāte, bijusī Izglītības un zinātnes ministre"`. Mans rule "role satur 'ministr'" klasificētu kā `minister`, lai gan viņa ir aktīva deputāte (rule a — pretī).

**Risinājums:** Split role pa komatiem un atfiltrē "bijuš" prefiksētus chunkus PIRMS substring match:

```python
chunks = [c.strip() for c in (role or "").split(",")]
active_chunks = [c for c in chunks if not re.match(r'^bijuš[aīi]\b', c.lower())]
active_role = ", ".join(active_chunks).lower()
# tagad pārbauda active_role pret 'ministr', 'EP deputāt', utt.
```

---

## 3. Fāze F1: Data layer (~85 līniju)

### F1.1: `src/profile_kind.py` (jauns fails, ~60 līniju)

Mirror `src/coalition.py` struktūru:
- Module docstring (kāpēc šis nav stored DB; kāpēc atsevišķs no relationship_type; kā saskan ar role labelu)
- `ProfileKind = Literal["deputy", "minister", "mep", "regional", "politician", "journalist", "analyst", "organization", "former", "inactive"]`
- `derive_profile_kind(relationship_type: str, role: Optional[str], current_term_vote_count: int) -> ProfileKind`
- `get_profile_kind_map(db) -> dict[int, ProfileKind]` — batch helper, key=politician_id

**Derivation rule order** (pirmā atbilstība uzvar; izmantot `active_role` no chunk-split):

```
1. relationship_type == 'inactive' → 'inactive'
2. relationship_type == 'journalist' → 'journalist'
3. relationship_type == 'organization' → 'organization'
4. relationship_type == 'neutral' → 'analyst'
5. active_role satur 'ministr' OR 'ministru prezident' OR 'valsts kanc' OR 'valsts prezident' → 'minister'
6. active_role satur 'ep deputāt' OR 'eiropas parlament' → 'mep'
7. active_role satur 'mērs' OR 'vicemērs' OR 'domes' → 'regional'
8. current_term_vote_count > 0 → 'deputy'
9. role.lower() satur 'bijuš' (jebkur, ne tikai prefiksēts) → 'former'
10. else → 'politician'
```

### F1.2: `tests/test_profile_kind.py` (~25 līniju)

```python
import pytest
from src.profile_kind import derive_profile_kind

@pytest.mark.parametrize("rel,role,votes,expected", [
    ("inactive", "Saeimas deputāts", 50, "inactive"),
    ("journalist", "Žurnālists", 0, "journalist"),
    ("organization", "Darba devēju interešu organizācija", 0, "organization"),
    ("neutral", "Politiskais analītiķis", 0, "analyst"),
    ("tracked", "Ministru prezidente", 0, "minister"),
    ("tracked", "Saeimas deputāte, bijusī Izglītības un zinātnes ministre", 50, "deputy"),  # bug fix verification
    ("tracked", "EP deputāts", 0, "mep"),
    ("tracked", "Rīgas mērs", 0, "regional"),
    ("tracked", "Saeimas deputāts", 70, "deputy"),
    ("tracked", "Bijušais Saeimas priekšsēdētājs", 0, "former"),
    ("tracked", "Valdes priekšsēdētājs", 0, "politician"),
    ("tracked", None, 0, "politician"),
])
def test_derive_profile_kind(rel, role, votes, expected):
    assert derive_profile_kind(rel, role, votes) == expected
```

### F1.3: `src/render/_common.py` re-eksports

Pievieno:
```python
from src.profile_kind import derive_profile_kind, ProfileKind
```
Pievieno `__all__` ja tāds eksistē (skaties pašreiz).

### F1 verifikācija (must pass before commit):

```bash
.venv/Scripts/python -m pytest tests/test_profile_kind.py -v
# Visi 12 parametrized testi zaļi
.venv/Scripts/python -c "from src.profile_kind import derive_profile_kind; \
    print(derive_profile_kind('tracked', 'Ministru prezidente', 0))"
# Output: minister
```

### F1 commit:

```
feat(profile_kind): derivation module + tests

Add domain logic for politician role classification, derived from
existing relationship_type + role + vote-activity signals. Mirrors
src/coalition.py pattern (small module, Literal enum, batch + single
helpers, rich docstring on why-not-stored-in-DB).

Used by upcoming role-aware profile tab dispatch in
src/render/politicians.py. Compute-at-render avoids schema migration
and stays in sync if `role` field changes downstream.
```

---

## 4. Fāze F2: Render layer (~95 līniju)

### F2.1: `src/render/politicians.py` paplašinājums

Pievieno helper funkcijas:

```python
def _profile_tab_set(kind: str) -> list[str]:
    """Return ordered tab IDs for a profile_kind."""
    mapping = {
        "deputy": ["timeline", "pozicijas", "saeima", "pretrunas", "saites"],
        "minister": ["timeline", "pozicijas", "pretrunas", "saites"],
        "mep": ["timeline", "pozicijas", "pretrunas", "saites"],
        "regional": ["timeline", "pozicijas", "pretrunas", "saites"],
        "politician": ["timeline", "pozicijas", "pretrunas", "saites"],
        "journalist": ["timeline", "komentari_by", "publikacijas"],
        "analyst": ["timeline", "komentari_by", "publikacijas"],
        "organization": ["timeline", "pozicija", "saites"],
        "former": ["timeline", "pozicijas", "saeima_historic", "pretrunas", "saites"],
        "inactive": ["timeline"],
    }
    return mapping.get(kind, ["timeline"])

def _fetch_commentary_by(db, pid: int) -> list[dict]:
    """Claims kur šis politiķis IR speaker (žurnālistu/analītiķu komentāri par citiem)."""
    # SELECT c.*, target.name as target_name FROM claims c
    # JOIN tracked_politicians target ON c.opponent_id = target.id
    # WHERE c.speaker_id = ? AND c.opponent_id != c.speaker_id
    # ORDER BY c.stated_at DESC LIMIT 50

def _fetch_saites_for_profile(db, pid: int, profile_kind: str) -> dict:
    """Apvieno tensions (split by type), commentary about, vote alignment.
    
    Returns:
        {
          'uzbrukumi': [...],
          'spriedzes': [...],
          'atbalsts': [...],
          'commentary_about': [...],
          'vote_alignment_top': [...] | None,  # tikai deputātiem
          'vote_alignment_bottom': [...] | None,
          'mini_graph': {nodes: [...], links: [...]},
        }
    """
    # tensions split: SELECT ... WHERE source_pid=? OR target_pid=? GROUP BY tension_type
    # commentary_about: existing _fetch_commentary_about
    # vote_alignment: tikai ja profile_kind == 'deputy'
    # mini_graph_data: combine top neighbors (max 8) for static SVG layout

def _vote_alignment_for(db, pid: int, top_n: int = 3) -> tuple[list, list]:
    """Top-N most/least aligned deputies. Returns (top, bottom) lists.
    
    O(N_deputies) per call; OK for one profile (called once per render).
    Re-implements links.py logic per F4 leaf rule (peer module isolation).
    Promote to _common.py if/when both consumers need same shape.
    """
```

Update `_fetch_politician_detail` (vai equivalentu callsite) to set:
```python
detail['profile_kind'] = derive_profile_kind(
    p['relationship_type'], p['role'],
    current_term_vote_count=detail.get('current_votes', 0)  # need to compute
)
detail['tab_set'] = _profile_tab_set(detail['profile_kind'])
detail['saites_data'] = _fetch_saites_for_profile(db, pid, detail['profile_kind'])
if detail['profile_kind'] in ('journalist', 'analyst'):
    detail['commentary_by'] = _fetch_commentary_by(db, pid)
```

### F2.2: `templates/politician.html.j2` izmaiņas

#### Header — pievieno role chip ar profile_kind klasi

Pēc `<span class="profile-party-tag">` rinda, pievieno:

```jinja
<span class="role-chip role-chip-{{ politician.profile_kind }}">
  {{ politician.role or 'Politiķis' }}
</span>
{% if 'bijuš' in (politician.role or '')|lower %}
<span class="role-chip role-chip-former">bijušais</span>
{% endif %}
```

#### Stat-bar — wrap visus tabu pogas conditionālos

```jinja
{% if 'pozicijas' in tab_set %}
<button class="profile-stat" ...>Pozīcijas</button>
{% endif %}
{% if 'saeima' in tab_set %}
<button class="profile-stat" ...>Saeimā</button>
{% endif %}
... utt
```

#### Tab content — wrap analoģiski

#### Saites tab — pārstrādāts ar 3 type-color sekcijām + mini-graf

```jinja
<div class="profile-tab" id="tab-saites" style="display:none;">
  {# Mini-graf: static SVG, ring layout #}
  <svg viewBox="0 0 400 280" class="mini-saites-graph">
    {% set center_x, center_y, radius = 200, 140, 90 %}
    {# Center node = this politician #}
    <circle cx="{{ center_x }}" cy="{{ center_y }}" r="14" 
            fill="{{ party_color }}" stroke="#fff" stroke-width="2"/>
    {# Neighbors in ring #}
    {% set total = saites_data.mini_graph.neighbors|length %}
    {% for n in saites_data.mini_graph.neighbors %}
      {% set angle = (loop.index0 / total) * 6.283 - 1.571 %}
      {% set nx = center_x + (radius * (angle|cos)) %}
      {% set ny = center_y + (radius * (angle|sin)) %}
      <line x1="{{ center_x }}" y1="{{ center_y }}" x2="{{ nx }}" y2="{{ ny }}"
            class="saites-link saites-link-{{ n.tension_type }}" stroke-width="2"/>
      <a xlink:href="../politiki/{{ n.slug }}.html">
        <circle cx="{{ nx }}" cy="{{ ny }}" r="9" 
                fill="{{ n.party_color }}" stroke="#fff"/>
        <title>{{ n.name }} ({{ n.tension_type }})</title>
      </a>
    {% endfor %}
  </svg>
  
  {# 3 type-color sekcijas #}
  {% if saites_data.uzbrukumi %}
  <div class="saites-section saites-section-uzbrukumi">
    <h4>Uzbrukumi ({{ saites_data.uzbrukumi|length }})</h4>
    {% for t in saites_data.uzbrukumi %}<div class="card">...</div>{% endfor %}
  </div>
  {% endif %}
  
  {% if saites_data.spriedzes %}
  <div class="saites-section saites-section-spriedzes">
    <h4>Spriedzes ({{ saites_data.spriedzes|length }})</h4>
    ...
  </div>
  {% endif %}
  
  {% if saites_data.atbalsts %}
  <div class="saites-section saites-section-atbalsts">
    <h4>Atbalsts ({{ saites_data.atbalsts|length }})</h4>
    ...
  </div>
  {% endif %}
  
  {% if saites_data.commentary_about %}
  <div class="saites-section">
    <h4>Komentāri par šo politiķi ({{ saites_data.commentary_about|length }})</h4>
    ...
  </div>
  {% endif %}
  
  {% if saites_data.vote_alignment_top %}
  <div class="saites-section">
    <h4>Visbiežāk balso vienādi</h4>
    {% for v in saites_data.vote_alignment_top %}...{% endfor %}
  </div>
  <div class="saites-section">
    <h4>Visretāk balso vienādi</h4>
    ...
  </div>
  {% endif %}
  
  <a href="../saites.html" class="see-full-graph-link">Skatīt pilnajā kartē →</a>
</div>
```

**SVG `cos`/`sin` filtri** — Jinja nav iebūvēti. Pievieno custom filtrus `_common.py` env setup (vai pre-compute koordinātas Python pusē un padod kā pre-rendered list — tīrāk).

**Pre-compute** ieteiktais ceļš:

```python
# politicians.py
def _saites_neighbors_with_coords(neighbors: list, cx=200, cy=140, r=90) -> list:
    import math
    out = []
    n = len(neighbors)
    for i, neighbor in enumerate(neighbors):
        angle = (i / n) * 2 * math.pi - math.pi/2
        out.append({**neighbor,
                    "x": cx + r * math.cos(angle),
                    "y": cy + r * math.sin(angle)})
    return out
```

Template ieaicina `n.x` un `n.y` tieši — nav `cos`/`sin` filtra.

#### Komentāri-by tab (jauns žurnālistiem/analītiķiem)

```jinja
{% if 'komentari_by' in tab_set %}
<div class="profile-tab" id="tab-komentari-by" style="display:none;">
  <p class="muted">{{ politician.name }} komentāri par citiem politiķiem ({{ commentary_by|length }})</p>
  {% for c in commentary_by %}
  <div class="card">
    <a href="../politiki/{{ c.target_slug }}.html">{{ c.target_name }}</a>:
    "{{ c.stance }}"
    <small>{{ c.stated_at[:10] }} · <a href="{{ c.source_url }}">avots</a></small>
  </div>
  {% endfor %}
</div>
{% endif %}
```

#### X+Ziņas merge zem Publikācijas vai zem Pozīcijas

Atkarīgs no `tab_set`. Ja `publikacijas` ir tab_set (žurnālistiem) — atsevišķs tabs ar abām merge'd. Ja ne — divi loops zem Pozīcijas tab pēc esošā claims loop.

### F2.3: CSS pamati (`assets/style.css` vai `templates/_styles_block.css.j2` — kur pašlaik ir profile-stat klases)

```css
.role-chip { display: inline-block; padding: 2px 8px; border-radius: 4px; 
             font-size: 0.75em; margin-left: 6px; }
.role-chip-deputy { background: #2563eb; color: white; }
.role-chip-minister { background: #16a34a; color: white; }
.role-chip-mep { background: #7c3aed; color: white; }
.role-chip-regional { background: #ca8a04; color: white; }
.role-chip-politician { background: #64748b; color: white; }
.role-chip-journalist { background: #475569; color: white; }
.role-chip-analyst { background: #059669; color: white; }
.role-chip-organization { background: #be185d; color: white; }
.role-chip-former { background: #f97316; color: white; }
.role-chip-inactive { background: #94a3b8; color: white; }

.saites-link-uzbrukums { stroke: #ef4444; }
.saites-link-spriedze  { stroke: #eab308; }
.saites-link-atbalsts  { stroke: #22c55e; }
.saites-link-vote      { stroke: rgba(139,92,246,0.5); stroke-dasharray: 3,2; }

.saites-section h4 { display: flex; align-items: center; gap: 8px; }
.saites-section-uzbrukumi h4::before { content: "■"; color: #ef4444; }
.saites-section-spriedzes h4::before { content: "■"; color: #eab308; }
.saites-section-atbalsts h4::before { content: "■"; color: #22c55e; }
```

### F2 verifikācija:

```bash
.venv/Scripts/python -c "from src.render import generate_public_site; generate_public_site()"
# Must complete without errors

# Open 3 sample profiles in browser, eyeball:
# - http://127.0.0.1:8080/politiki/edvins-snore.html (deputy)
# - http://127.0.0.1:8080/politiki/evika-silina.html (minister)
# - http://127.0.0.1:8080/politiki/lato-lapsa.html (journalist)

# Pytest WILL fail on test_render_chars — that's expected
.venv/Scripts/python -m pytest tests/test_render_chars.py 2>&1 | tail -20
# Politicians fixture failures are OK; they get fixed in REGEN phase
```

### F2 commit:

```
feat(profile): role-aware tab dispatch + Saites mini-graf

- _profile_tab_set(kind) maps profile_kind to ordered tab list
- _fetch_saites_for_profile splits tensions by tension_type + adds
  vote alignment top/bottom for deputies + pre-computed mini-graph
  coords (static SVG ring layout, no JS)
- _fetch_commentary_by for journalist/analyst profiles
- politician.html.j2: tab visibility per tab_set, header role chip,
  Saites tab type-color sections, static SVG mini-graf, X+Ziņas
  merge under Pozīcijas (or Publikācijas for journalists)
- CSS: role-chip-* per profile_kind, saites-link/section colors

Char-fixture failures expected — REGEN in next commit.
```

---

## 5. Fāze REGEN: Char-fixture baseline (~1 commit, no code changes)

### REGEN soļi:

```bash
REGEN=1 .venv/Scripts/python -m pytest tests/test_render_chars.py -v
# Politicians fixture (~150 hashes) flips
# Other fixtures should remain stable

git diff tests/fixtures/render_baseline_politicians.json | head -30
# Sanity check: jaunie hashes look normal

git add tests/fixtures/render_baseline_politicians.json
# (Maybe also misc/dashboard if some count changed downstream)
```

### Operatora diff review (kritisks!):

Atver 3-5 politicians.html failus output/ atomā un eyeball diff vs git HEAD:
- Šnore: 5 tabi parādās, role chip "Saeimas deputāts", Saites tab type-color sekcijas
- Siliņa: 4 tabi (NAV Saeimā), role chip "Ministru prezidente"
- Lapsa: 3 tabi (Komentāri-by primary)

Ja kāds profils izskatās salauzts — STOP, atrod bug, fix, atkārto REGEN.

### REGEN commit:

```
test(render): regen politicians baseline for role-aware tabs

Politician HTML rendering changed in F2 (tab visibility per
profile_kind, header role chips, Saites tab type-color sections,
static SVG mini-graf). Operator diff-reviewed 5 sample profiles —
output matches design intent.

Per char-fixture convention (CHANGELOG 2026-04-30 drift catch),
REGEN runs as separate commit before polish phase.
```

---

## 6. Fāze F3: Polish + smoke test (~30 līniju + manual)

### F3.1: 8-profilu smoke test

Atver browseri katram profile_kind klasei un pārbauda:

| # | profile_kind | URL | Sagaidāms |
|---|---|---|---|
| 1 | deputy | `politiki/edvins-snore.html` | 5 tabi (incl Saeimā), chip "Saeimas deputāts" zils |
| 2 | minister | `politiki/evika-silina.html` | 4 tabi (NAV Saeimā), chip "Ministru prezidente" zaļš |
| 3 | mep | `politiki/ansis-pupols.html` | 4 tabi, chip "EP deputāts" violet |
| 4 | regional | `politiki/viesturs-kleinbergs.html` | 4 tabi, chip "Rīgas mērs" oranžs |
| 5 | politician | `politiki/alvis-hermanis.html` | 4 tabi, chip "Valdes priekšsēdētājs" pelēks |
| 6 | journalist | `politiki/lato-lapsa.html` | 3 tabi (Komentāri-by + Publikācijas), nav Pozīcijas/Pretrunas |
| 7 | analyst | `politiki/filips-rajevskis.html` | 3 tabi, chip "Politiskais analītiķis" emerald |
| 8 | organization | (kāds LDDK profils ja eksistē) | 3 tabi (Pozīcija + Saites) |

Plus pārbaudi:
- Mini-graf SVG ielādējas, neaiziet ārā no kompozīcijas
- Klikšķi uz kaimiņa mezgla → atver tā profilu
- Tension type sekcijas ar pareizām krāsām
- "Skatīt pilnajā kartē" link strādā

### F3.2: Final test + check

```bash
bash scripts/check.sh
# Must exit 0 — visi testi zaļi, ruff clean, generate_public_site smoke OK
```

### F3.3: Commit + PR

```
feat(profile): tension type colors + role chip styling polish

CSS finalization for F2 role-aware tab refactor — color tokens for
all 10 profile_kind chips and 3 tension_type sections. Smoke-tested
on 8 sample profiles (one per profile_kind class).

Reviewer notes: see PR description for screenshots and 8-profile
smoke test report.
```

```bash
git push -u origin feat/profile-roles
gh pr create --title "feat(profile): role-aware tabs + Saites mini-graf" --body "..."
```

PR description satur 8-profile screenshot mosaic + linka uz šo plāna failu.

---

## 7. Acceptance criteria (final gate)

- [ ] `pytest tests/test_profile_kind.py` — 12/12 zaļi
- [ ] `pytest tests/test_render_chars.py` — visi zaļi pēc REGEN
- [ ] `bash scripts/check.sh` — exit 0
- [ ] 8-profile smoke test — visi izskatās korekti
- [ ] Šnera profilam 5 tabi, Siliņas profilam 4 (NAV Saeimā), Lapsas profilam 3
- [ ] Mini-graf ielādējas bez JS errors
- [ ] Klikšķi uz mini-graf kaimiņa → tā profils
- [ ] Tension type sekcijas (uzbrukumi/spriedzes/atbalsts) ar pareizām krāsām
- [ ] PR: 4 commits, clean (F1, F2, REGEN, F3)

---

## 8. Edge cases — manuālā verifikācija

Pēc F1 saglabāt SQL audit-skriptu izvades:

```bash
.venv/Scripts/python -c "
from src.db import get_db
from src.profile_kind import derive_profile_kind
db = get_db()
rows = db.execute('SELECT id, name, party, relationship_type, role FROM tracked_politicians WHERE relationship_type != \"inactive\"').fetchall()
for r in rows:
    votes = db.execute('SELECT COUNT(*) FROM saeima_individual_votes siv JOIN saeima_votes sv ON siv.vote_id=sv.id WHERE siv.politician_id=? AND sv.vote_date>=\"2022-11-01\"', (r['id'],)).fetchone()[0]
    kind = derive_profile_kind(r['relationship_type'], r['role'], votes)
    print(f'{r[\"id\"]:>3} {kind:<14} | {r[\"name\"][:30]:<30} | role={(r[\"role\"] or \"-\")[:50]}')
" | sort -k2,2
```

Pārbaudi šādus edge cases manuāli:

- **Hermanis** (rel=tracked, role='Valdes priekšsēdētājs', votes=0) → ekspektē `politician`
- **Lapsa** (rel=journalist, 53 "positions") → ekspektē `journalist`. Verificē, ka 53 claims tiešām ir `claim_type='commentary'` ar speaker_id=57, ne first-party. Ja ne — datu bug, ne profile_kind bug.
- **"Saeimas deputāte, bijusī Izglītības un zinātnes ministre"** → ekspektē `deputy` (rule 8 wins jo bijus prefix sten chunk-split)
- **"NA priekšsēdētājs, Saeimas deputāts"** → ekspektē `deputy` (rule 8)
- **"Bijušais Saeimas priekšsēdētājs"** → ekspektē `former` (rule 9, jo neviens cits aktīvs match)
- **Saeimas ziņas** (rel=organization) → ekspektē `organization`. Datu-driven: ja 0 first-party pozīcijas, slēpj Pozīciju tabu (template `{% if positions %}` esošais conditional)
- **LDDK** (rel=organization) → ekspektē `organization`. Ja ir institucionālās pozīcijas → Pozīcija tab parādās.
- **Bartaševičs/Tutins** ("Kopā Latvijai" — nav LPV — sk. memory `project_kopa_latvijai_party.md`). Verificē, ka party tag headerā ir korekts.

Ja kāds gadījums nesakrīt — analīze, fix derivation rules vai source data, atkārto F1 testus.

---

## 9. Rollback plan

Worktree izolē master, tāpēc rollback ir vienkāršs:

```bash
# Ja kāda fāze sajaukta: revert pēdējo commit
git reset --hard HEAD~1

# Ja viss PR jāatmet: 
cd "~/atmina"
git worktree remove .worktrees/profile-roles
git branch -D feat/profile-roles
```

DB nemainās (compute at render), wiki nemainās — pure code change.

---

## 10. Future work (NE šajā PR)

- **F4.1: Personas filtra extension** — pievienot profile_kind filtru Personas lapai (memory `project_restructuring_plan.md`: "Personas ar filtriem")
- **F4.2: Ministra resorā lēmumu tracker** — MK rīkojumi, MK noteikumi, parakstītāji
- **F4.3: EP vote tracker** — Eiropas Parlamenta balsojumu integrācija MEP profiliem
- **F4.4: Domes balsojumi** — pašvaldības profiliem (Rīgas dome u.c.)
- **F4.5: Vote-alignment promotion uz `_common.py`** — ja `links.py` arī sāk lietot per-pid shape (šobrīd O(N²) form)
- **F4.6: Saites lapas filtra extension** — pa profile_kind nodes coloring
- **F4.7: Org advocacy vs press split** — ja Saeimas ziņas + LDDK plūsma sajaucas operators noslodzē

---

## 11. Sesijas konteksta apkopojums

Šī plāna izejas konteksts (Telegram sesija 2026-05-01):

1. Lietotājs pamanīja "1 spriedze" Šlesera profilā pēc tension #90 dzēšanas (kas bija type='uzbrukums'). Tas atklāja "Spriedzes" stat-poga lumping problēmu.
2. Lietotājs paprasīja: "lai nav par daudz tabu un viss ir intuitīvi"
3. Iziets cauri 9-tabu konsolidācijai (α 4-tabi vs β 5-tabi). Lietotājs izvēlējās β.
4. Iziets cauri role distinction (deputy/minister/mep/.../organization) — 10 kategorijas
5. Iziets cauri Saites tab struktūru (3 varianti: minimāls/vidējs/bagāts). Lietotājs izvēlējās Variants 2 (mini-graf + sekcijas).
6. Lietotājs apstiprināja izvēles uz a/b/c/d jautājumiem
7. Pirmais ultrathink atrada 5 flaws + 4 vienkāršošanas iespējas, samazinot apjomu 320 → 140 līnijas
8. Otrais ultrathink (wiki alignment) atrada 3 must-fix neatbilstības — galvenā: separate module `src/profile_kind.py` (kā `coalition.py`), char-fixture REGEN, regex bug

Trešais ultrathink šajā plāna failā konsolidē visus iepriekš pieņemtos lēmumus + arhitektūras precedents.

---

## 12. Ja iesāc kā jaunā sesijā

1. Pārliecinies par worktree (sekcija 0)
2. Lasi šo plānu visā garumā
3. Lasi `CLAUDE.md` (datu kontrakti, F4 leaf rule)
4. Lasi `wiki/CHANGELOG.md` § F3a-F3g (render moduļa F4 precedents) un § 2026-04-30 drift catch (REGEN konvencija)
5. Lasi `src/coalition.py` (precedents jaunajam `src/profile_kind.py`)
6. Glance `src/render/politicians.py` un `templates/politician.html.j2` (kur veiksi izmaiņas)
7. Sāc F1 (sekcija 3)
8. Pēc katras fāzes commit + verify, pirms nākamās

Veiksmi!
