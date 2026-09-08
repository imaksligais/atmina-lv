# Sākumlapas pievilcības pārveide — implementācijas plāns

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sākumlapa ar sejām, redzamu vēlēšanu countdown, zīmola krāsu grafikiem un ilustrācijām pirmajā ekrānā — tikai no esošiem resursiem (spec: `docs/superpowers/specs/2026-07-04-landing-redesign-design.md`).

**Architecture:** Viss darbs 4 failos: `templates/index.html.j2` (markups + sekciju secība + chart datu padeve), `src/render/dashboard.py` (konteksta bagātināšana: has_photo, brīvlaika fakts, chart krāsas), `assets/style.css` (jaunie bloki), + hermētiski testi jaunajiem helperiem. Renderēšana caur esošo `generate_public_site()`; char-baselines pārsvētī beigās centralizēti.

**Tech Stack:** Jinja2, Python 3.12 (venv `./.venv/Scripts/python.exe`), Chart.js (jau ir, `defer`), rokrakstīts CSS ar tēmu tokeniem.

**Zināšanas izpildītājam (bez šī konteksta nesāc):**
- Foto: `output/atmina/assets/photos/<slug>.jpg`; eksistences pattern skat. `templates/index.html.j2:33-36` (`c.has_photo` → `<img …photos/{{ c.slug }}.jpg…>` ar iniciāļu fallback `<span class="hero-feature-avatar" style="--pc: {{ c.party_color }}">{{ c.initials }}</span>`).
- Rangi dati: `src/render/rankings.py::fetch_rankings` — ieraksti jau satur `name`, `slug`, `party`, `party_color` (rindas ~58-88). Kategorijas: `most_contradictions`, `biggest_reversals`, `most_active_7d`, `vote_alignment_outliers`; templotē `templates/index.html.j2:98-176`.
- Krāsas: `src/render/_common.py:74` `PARTY_COLORS`, `:90` `TOPIC_COLORS`.
- `days_until_election` jau ir index kontekstā (`dashboard.py` ~298); hero čipu atrodi templotē pēc šī mainīgā.
- `week_summary` būve: `dashboard.py:277-282` (`claims_7d`, `votes_7d`, `contradictions_7d`); templotē `.week-strip` ap `index.html.j2:180`.
- Chart canvas: `index.html.j2:409-417` (`topicsChart`, `politiciansChart`); inicializācijas JS ir tās pašas templotes `{% block scripts %}` daļā — atrodi ar `grep -n "topicsChart" templates/index.html.j2`. Datu masīvi tiek emitēti caur `safe_json` filtru (pattern jau lietots templotē).
- KONVENCIJA: datu-krāsu-TEKSTU emitē caur `--party-color` custom prop (ne inline `color:`); canvas grafiki ir izņēmums (JS krāsas OK). Sk. `~/.claude/...atmina/memory/project_light_theme_2026-06-13.md`.
- NEDRĪKST: `templates/base.html.j2`, `_CHROME_SPECS`, curated statistika*/finanses, jaunas JS bibliotēkas.
- Testu stils: hermētiski, bez `data/atmina.db` — skat. `tests/test_search_index.py` un `tests/test_synthesis_image_variants.py`.
- Baselines: pēc HTML izmaiņām `tests/test_render_chars.py` KRITĪS — tas ir gaidīts; REGEN tikai Task 7.

---

### Task 1: Brīvlaika fakts "Šonedēļ" joslā (datu helpers ar testu)

**Files:**
- Modify: `src/render/dashboard.py`
- Test: `tests/test_dashboard_week_facts.py` (jauns)
- Modify: `templates/index.html.j2` (~:180 `.week-strip` bloks)

- [ ] **Step 1: Uzraksti krītošu testu**

```python
"""Šonedēļ joslas fakti: 0 vietā rāda pēdējās aktivitātes datumu (nevis mirušu nulli)."""
from src.render.dashboard import week_fact


def test_week_fact_zero_uses_last_date():
    assert week_fact(0, "2026-06-11", "balsojumu") == "pēdējie balsojumu · 11.06.2026"


def test_week_fact_nonzero_returns_none():
    assert week_fact(5, "2026-06-11", "balsojumu") is None


def test_week_fact_zero_without_date():
    assert week_fact(0, None, "balsojumu") is None
```

NB: formulējuma precīzo LV formu drīksti uzlabot (piem. "pēdējie balsojumi 11.06."), bet tad sinhronizē testu — gramatikas vārti: dabiska latviešu valoda, bez kalkiem.

- [ ] **Step 2: Palaid — jākrīt ar ImportError/AttributeError**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_dashboard_week_facts.py -q`

- [ ] **Step 3: Implementē `week_fact` + iesaisti kontekstā**

`dashboard.py` (pie pārējiem moduļa helperiem, pirms `_render_page` izsaukuma vietas):

```python
def week_fact(count: int, last_date: str | None, noun_gen: str) -> str | None:
    """0-vērtības vietā cilvēcīgs fakts ("Saeima brīvlaikā" sajūtas novēršana).

    Atgriež None, ja skaitītājs > 0 (tad rāda parasto ciparu) vai nav datuma.
    """
    if count or not last_date:
        return None
    d = f"{last_date[8:10]}.{last_date[5:7]}.{last_date[:4]}" if len(last_date) >= 10 else last_date
    return f"pēdējie {noun_gen} · {d}"
```

`week_summary` dict (`dashboard.py:277-282`) papildini ar:

```python
        "votes_fact": week_fact(stats.get("votes_7d", 0), (recent_votes[0]["vote_date"] if recent_votes else None), "balsojumi"),
        "contradictions_fact": week_fact(hero_data.get("contradictions_7d", 0), (contradictions[0].get("new_date") if contradictions else None), "pretrunas"),
```

(`recent_votes` un `contradictions` jau ir pieejami šajā funkcijā — pārbaudi faktiskos mainīgo vārdus ar grep un pielāgo.)

- [ ] **Step 4: Templotē `.week-strip` (index.html.j2 ~:180): ja fakts ir, rādi to skaitļa vietā**

Atrodi bloku, kur rādās `votes_7d`/`contradictions_7d`, un katram:

```jinja
{% if week_summary.votes_fact %}
  <div class="week-stat week-stat-fact">{{ week_summary.votes_fact }}</div>
{% else %}
  … (esošais cipara bloks nemainīts) …
{% endif %}
```

CSS `assets/style.css` (pie week-strip stiliem): `.week-stat-fact { color: var(--text-muted); font-size: 0.85rem; align-self: center; }` — pielāgo apkārtējam markupam, lai rinda līdzinās.

- [ ] **Step 5: Testi zaļi + renders**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_dashboard_week_facts.py -q` → PASS
Run: `./.venv/Scripts/python.exe -c "from src.render import generate_public_site; generate_public_site(only='dashboard')"` un `grep -o "pēdējie [^<]*" output/atmina/index.html`

- [ ] **Step 6: Commit**

```bash
git add src/render/dashboard.py templates/index.html.j2 assets/style.css tests/test_dashboard_week_facts.py
git commit -m "feat(dashboard): Šonedēļ joslā 0 vietā pēdējās aktivitātes fakts"
```

---

### Task 2: has_photo rangiem + Līderu josla ar sejām

**Files:**
- Modify: `src/render/rankings.py` (katram ierakstam `has_photo`)
- Modify: `templates/index.html.j2:98-176` (Rangi sekcija)
- Modify: `assets/style.css`
- Test: `tests/test_rankings_photco.py` NAV vajadzīgs atsevišķs — paplašini esošo rankings testu, ja tāds ir (`grep -rn "fetch_rankings" tests/`); ja nav, pievieno minimālu hermētisku testu par `has_photo` atvasināšanu.

- [ ] **Step 1: `rankings.py` — has_photo lauks**

Foto direktoriju noskaidro: `grep -rn "photos" src/render/_common.py src/render/personas.py | head` (personas lapa jau dara tieši šo pārbaudi — ATKĀRTO to pašu mehānismu, nevis izgudro; visticamāk `(ASSETS_DIR / "photos" / f"{slug}.jpg").exists()` vai konteksta lauks no orchestratora). Katrā no 4 kategoriju ierakstiem pievieno `"has_photo": <tas pats izteikums>`.

- [ ] **Step 2: Templotē — kolonnas #1 kā mini-kartīte, pārējie ar 20px avatāru**

Katrai no 4 kolonnām (`index.html.j2:108-176`) pārveido ciklu pēc parauga (pattern identisks visām četrām; rādīts viens):

```jinja
{% for r in rankings.most_contradictions[:8] %}
  {% if loop.first %}
  <a href="politiki/{{ r.slug }}.html" class="rank-leader" style="--pc: {{ r.party_color }}">
    {% if r.has_photo %}<img class="rank-leader-photo" src="assets/photos/{{ r.slug }}.jpg" alt="" width="44" height="44" loading="lazy">
    {% else %}<span class="rank-leader-photo rank-leader-initials">{{ r.name.split()[0][0] }}{{ r.name.split()[-1][0] }}</span>{% endif %}
    <span class="rank-leader-name">{{ r.name }}</span>
    <span class="rank-leader-value">{{ r.value }}</span>
  </a>
  {% else %}
  <a href="politiki/{{ r.slug }}.html" class="rank-row">
    {% if r.has_photo %}<img class="rank-row-photo" src="assets/photos/{{ r.slug }}.jpg" alt="" width="20" height="20" loading="lazy">{% else %}<span class="rank-row-photo rank-row-initials" style="--pc: {{ r.party_color }}"></span>{% endif %}
    <span class="rank-row-name">{{ r.name }}</span><span class="rank-row-value">{{ r.value }}</span>
  </a>
  {% endif %}
{% endfor %}
```

SVARĪGI: pirms pārrakstīšanas izlasi esošo kolonnas markupu — vērtības lauks katrā kategorijā atšķiras (piem. `cnt`, `delta_days`, procenti ar piezīmi ceturtajā kolonnā). Saglabā esošos vērtību izteikumus un kolonnu virsrakstus/piezīmes; maini tikai rindas formu.

- [ ] **Step 3: CSS**

```css
/* Līderu josla — Rangi ar sejām (landing redesign 2026-07-04). */
.rank-leader { display: flex; align-items: center; gap: 0.6rem; padding: 0.5rem 0.6rem; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 0.5rem; text-decoration: none; color: var(--text); background: var(--surface); }
.rank-leader:hover { border-color: var(--accent); }
.rank-leader-photo { width: 44px; height: 44px; border-radius: 50%; object-fit: cover; border: 2px solid var(--pc, var(--border)); flex-shrink: 0; }
.rank-leader-initials { display: inline-flex; align-items: center; justify-content: center; font-size: 0.8rem; font-weight: 600; color: var(--pc, var(--text-muted)); background: color-mix(in srgb, var(--pc, var(--border)) 18%, transparent); }
.rank-leader-name { font-weight: 600; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-leader-value { margin-left: auto; font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 0.9rem; }
.rank-row { display: flex; align-items: center; gap: 0.45rem; padding: 0.28rem 0.2rem; text-decoration: none; color: var(--text-muted); font-size: 0.85rem; }
.rank-row:hover { color: var(--text); }
.rank-row-photo { width: 20px; height: 20px; border-radius: 50%; object-fit: cover; flex-shrink: 0; }
.rank-row-initials { background: color-mix(in srgb, var(--pc, var(--border)) 22%, transparent); }
.rank-row-name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-row-value { margin-left: auto; font-family: "JetBrains Mono", ui-monospace, monospace; }
```

Gaišajā tēmā krāsas nāk no tokeniem — atsevišķs override nav vajadzīgs; vizuāli pārbaudi ABAS tēmas.

- [ ] **Step 4: Renders + acu pārbaude**

`generate_public_site(only='dashboard')`; atver `output/atmina/index.html` ar Playwright (`python -m http.server`) 1440px — foto ielādējas, iniciāļu fallback bez foto, kolonnas līdzinās.

- [ ] **Step 5: Commit** — `feat(dashboard): Rangi → Līderu josla ar politiķu foto`

---

### Task 3: Sekciju pārkārtošana

**Files:** Modify: `templates/index.html.j2`

- [ ] **Step 1:** Pārvieto veselas `<section>` blokus jaunajā secībā: Hero → Pārskati ("Jaunākie pārskati", meklē pēc virsraksta) → Pretrunas ("Jaunākās pretrunas") → Līderu josla (ex-"Rangi", :98-176 bloks) → "Šonedēļ" week-strip (atstāj pie Pretrunām vai zem Līderu joslas — izvēlies, kur vizuāli labāk, bet ne pirmais) → Analīzes → Tendences → Balsojumi. Pārvieto TIKAI veselus `{% if %}…{% endif %}` sekciju blokus, nesadalot tos.
- [ ] **Step 2:** Renders + vizuāli: sekciju secība pareiza, neviens bloks nav pazudis (`grep -c "section-head-title" output/atmina/index.html` pirms/pēc vienāds).
- [ ] **Step 3: Commit** — `feat(dashboard): sekciju secība — ilustrētie pārskati pirmajā ekrānā`

---

### Task 4: Hero asināšana + vēlēšanu countdown bloks

**Files:** Modify: `templates/index.html.j2` (hero, :27-63 + čips), `assets/style.css`

- [ ] **Step 1: Karuseļa kartes akcenti (CSS-pārsvarā):** `.hero-feature-avatar` 42→56px (arī `width`/`height` atribūti templotē :34-36), `.hero-feature-stance` fontu +1 solis (piem. 0.95rem, pārbaudi esošo), meta rindu (`.hero-feature-badge`) klusina (`opacity: .8; font-size: -1 solis`). Pretstatījuma bulta `.hero-feature-arrow` — lielāka (1.4rem) un akcenta krāsā.
- [ ] **Step 2: Countdown bloks.** Atrodi esošo čipu (grep `days_until_election` templotē). Aizstāj/paplašini ar:

```jinja
<div class="hero-election" role="note">
  <span class="hero-election-days">{{ days_until_election }}</span>
  <span class="hero-election-text">dienas līdz 15. Saeimas vēlēšanām<br>
    <a href="partijas.html">Partiju programmas →</a></span>
</div>
```

CSS: kompakts bloks hero labajā pusē / zem meklētāja (skaties, kur esošais čips sēž — paliec tajā zonā, tikai lielāks): `border: 1px solid var(--border); border-radius: 8px; padding: .5rem .8rem; display: inline-flex; gap: .6rem; align-items: center;` `.hero-election-days { font-size: 1.6rem; font-weight: 700; font-family: JetBrains Mono…; color: var(--accent); }`. LV locījumi: "{{ days_until_election }} dienas" der 91/92/94…; ja dienu skaits var būt 21/31/1 — lieto esošo `lv_plural` filtru: `{{ days_until_election }} {{ days_until_election|lv_plural("diena", "dienas") }}`.

- [ ] **Step 3:** Renders + vizuāli abās tēmās (countdown salasāms, hero nesabrūk 375px).
- [ ] **Step 4: Commit** — `feat(hero): vēlēšanu countdown bloks + karuseļa dueļa akcenti`

---

### Task 5: Pretrunu karšu clamp + citātu dominante

**Files:** Modify: `templates/index.html.j2` (Jaunākās pretrunas sekcija; markup ap :253 avatāriem), `assets/style.css`

- [ ] **Step 1:** Kopsavilkuma elementam (atrodi `KOPSAVILKUMS` bloku pretrunu kartē) pievieno klasi `.contra-summary-clamp`:

```css
.contra-summary-clamp { display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
```

- [ ] **Step 2:** `.prv2-avatar` šajās kartēs 40→56px (templotē width/height atribūti :254 un CSS ja fiksēts). Citātu paneļiem (`IEPRIEKŠ`/`PAŠLAIK` bloki) — fonts +1 solis, kopsavilkumam `color: var(--text-muted)`.
- [ ] **Step 3:** Renders + vizuāli: karte manāmi īsāka, citāti dominē, "Skatīt pretrunu" ceļš strādā.
- [ ] **Step 4: Commit** — `feat(dashboard): pretrunu kartēs citātu duelis priekšplānā, kopsavilkums clamped`

---

### Task 6: Tendenču grafiki zīmola krāsās

**Files:** Modify: `src/render/dashboard.py` (chart krāsu saraksti kontekstā), `templates/index.html.j2` (chart init JS)

- [ ] **Step 1: dashboard.py** — tur, kur būvē topic/politician chart datus (atrodi ar `grep -n "topics\|politicians" src/render/dashboard.py` ap chart konteksta vietu), pievieno paralēlus krāsu sarakstus:

```python
from src.render._common import TOPIC_COLORS, PARTY_COLORS  # ja vēl nav importēti
FALLBACK = "#8b8fa3"
topic_colors = [TOPIC_COLORS.get(t, FALLBACK) for t in topic_labels]
politician_colors = [PARTY_COLORS.get(p["party"], FALLBACK) for p in active_politicians]
```

(Reālos mainīgo vārdus paņem no koda; ja politiķu datiem nav party lauka, pievieno to vaicājumā vai lieto party_color, ja jau ir.) Padod kontekstā `topic_chart_colors`, `politician_chart_colors`.

- [ ] **Step 2: index.html.j2 chart init** (grep `topicsChart` scripts blokā) — aizstāj fikso `backgroundColor` ar:

```js
backgroundColor: {{ topic_chart_colors|safe_json }},
```

un politiķu grafikam attiecīgi `politician_chart_colors`. Ja krāsa jāpadara caurspīdīgāka, JS pusē `colors.map(c => c + 'B3')` (70% alpha hex) — vienādi abām tēmām.

- [ ] **Step 3:** Renders; atver abas tēmas — stabiņi vairs nav Chart.js zilie; krāsas atbilst tēmu/partiju kartēm citur lapā.
- [ ] **Step 4: Commit** — `feat(dashboard): tendenču grafiki TOPIC_COLORS/partiju krāsās`

---

### Task 7: Gala vārti + deploy

- [ ] **Step 1:** `REGEN=1 ./.venv/Scripts/python.exe -m pytest tests/test_render_chars.py -q` → skipped; tad bez REGEN → `24 passed`. Commit baselines: `test(chars): baselines pēc landing redesign`.
- [ ] **Step 2:** `bash scripts/check.sh` → `==> all checks passed` (citē asti).
- [ ] **Step 3:** Pilnais renders + Playwright: 1440px un 375px, gaišā UN tumšā tēma, pilnas lapas ekrānuzņēmumi; pārbaudi: sekciju secība, foto ielādes (`document.images` naturalWidth>0 pārbaude ar lazy-scroll triku — vispirms noskrollē līdz apakšai), countdown, chart krāsas, hero 375px nesabrūk, nav horizontālā scroll (`document.documentElement.scrollWidth <= innerWidth`).
- [ ] **Step 4:** OPERATORA APSTIPRINĀJUMS pirms deploy (parādi ekrānuzņēmumus — tas ir redakcionāls dizaina lēmums). Tad `bash scripts/deploy.sh --no-delete` + live pārbaudes (curl: foto 200, `grep -c hero-election`, chart krāsu JSON lapā).
- [ ] **Step 5:** BACKLOG.md — atzīmē landing redesign kā DONE pie UI review ieraksta. Commit.

## Self-review piezīmes

- Spec 6 prasības → Task 1 (nulles), 2 (līderu josla), 3 (secība), 4 (hero+countdown), 5 (pretrunu kartes), 6 (grafiki); Task 7 = verifikācija — pārklājums pilns.
- Vērtību lauki rangu kategorijās NAV unificēti (`cnt`/`delta_days`/procenti) — tāpēc Task 2 Step 2 liek saglabāt esošos izteikumus; tas ir apzināts, ne placeholder.
- Precīzas rindu numuru atsauces var būt nobīdījušās par ±pāris rindām pret master HEAD (e236fe9+) — grep enkuri doti katram gadījumam.
