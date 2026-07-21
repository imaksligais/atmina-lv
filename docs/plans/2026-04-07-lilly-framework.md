# Lilly Framework Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Layer Lilly's self-metaprogramming methodology onto the existing research-backed agent architecture — source framing awareness, evasion detection, confidence drift monitoring, alternative explanations on contradictions, and belief experiments.

**Architecture:** All changes layer onto existing files. No new infrastructure. 4 agent prompt edits, 1 YAML edit, 1 template edit, 2 Python code additions, 1 CLAUDE.md update.

**Tech Stack:** Existing — Python, SQLite, Jinja2 templates, agent markdown prompts.

---

## File Map

| File | Change |
|---|---|
| `sources.yaml` | Add `framing:` field per source |
| `.claude/agents/claim-extractor.md` | Add evasion risk self-awareness |
| `.claude/agents/devils-advocate.md` | Add evasion check question + belief experiment methodology |
| `.claude/agents/brief-writer.md` | Add evasion risk self-awareness |
| `.claude/agents/quality-reviewer.md` | Add evasion risk self-awareness |
| `src/confidence_drift.py` | NEW — confidence drift detection |
| `src/routine.py` | Add Step 0 interlock check + confidence drift |
| `templates/pretrunas.html.j2` | Add "Alternatīvs skaidrojums" section per contradiction |
| `src/generate.py` | Pass alternative explanations to template |
| `CLAUDE.md` | Add Step 0 interlock, monthly belief experiment, source framing context |

---

## Task 1: Source Framing in sources.yaml

**Files:**
- Modify: `sources.yaml`

- [ ] **Step 1: Add framing field to each active source**

Add a `framing:` field to each Tier 1 and Tier 2 source in `sources.yaml`. This characterizes what "simulation" each outlet runs — not bias scoring, but editorial frame awareness.

```yaml
sources:
  - url: "https://www.lsm.lv/rss/?lang=lv&catid=20"
    name: "LSM.lv Latvija"
    framing: "Valsts sabiedriskais medijs — institucionāli neitrāls, tendēts uz valdības pozīcijas atspoguļošanu, izvairās no spekulācijām"
    tier: 1
    # ... rest unchanged

  - url: "https://www.lsm.lv/rss/?lang=lv&catid=22"
    name: "LSM.lv Ekonomika"
    framing: "Valsts sabiedriskais medijs — ekonomikas fokuss, ministru un institūciju perspektīva dominē"
    tier: 1

  - url: "https://www.diena.lv/rss/?c=3"
    name: "Diena.lv Latvijā"
    framing: "Liberāli centriskā dienas avīze — balansēta ziņošana ar vieglu pro-ES un pro-reformu tendenci"
    tier: 1

  - url: "https://www.diena.lv/rss/?c=190"
    name: "Diena.lv Viedokļi"
    framing: "Viedokļu sadaļa — redakcijas atlasīti autori, tendēti uz liberālu-konservatīvu centru"
    tier: 1

  - url: "https://www.tvnet.lv/rss"
    name: "TVNet RSS"
    framing: "Komercportāls — optimizēts engagement, sensacionālāki virsraksti, plašāks tēmu diapazons"
    tier: 1

  - url: "https://www.delfi.lv/"
    name: "Delfi.lv"
    framing: "Lielākais ziņu portāls — engagement optimizēts, ātrs uz breaking news, plašs autoru loks ar dažādām perspektīvām"
    tier: 2

  - url: "https://rus.delfi.lv/"
    name: "rus.Delfi.lv"
    framing: "Krievvalodīgā auditorija — tās pašas ziņas bet ar krievvalodīgo kopienas perspektīvu un uzsvaru uz mazākumtautību jautājumiem"
    tier: 2

  - url: "https://www.leta.lv/"
    name: "LETA"
    framing: "Nacionālā ziņu aģentūra — visfaktoloģiskākais avots, minimāla interpretācija, oficiālie paziņojumi un preses konferences"
    tier: 2

  - url: "https://nra.lv/"
    name: "Neatkarīgā"
    framing: "Konservatīvi nacionāla avīze — kritiskāka pret koalīciju, nacionālo interešu fokuss, vairāk opozīcijas perspektīvas"
    tier: 2

  - url: "https://nra.lv/viedokli/"
    name: "Neatkarīgā Viedokļi"
    framing: "Viedokļi no konservatīvi nacionāla skatu punkta — bieži opozīcijas un neatkarīgo ekspertu autori"
    tier: 2
```

- [ ] **Step 2: Commit**

```bash
cd ~/atmina
git add sources.yaml
git commit -m "feat: add editorial framing characterization to all news sources"
```

---

## Task 2: Agent Evasion Risk Self-Awareness

Add Lilly-derived evasion risk awareness to all 4 primary agents. Each agent gets its own metaprogrammatic failure mode.

**Files:**
- Modify: `.claude/agents/claim-extractor.md`
- Modify: `.claude/agents/devils-advocate.md`
- Modify: `.claude/agents/brief-writer.md`
- Modify: `.claude/agents/quality-reviewer.md`

- [ ] **Step 1: Add evasion risk to @claim-extractor**

Read `.claude/agents/claim-extractor.md`. After the "Emotional Context" section (after the circuit breaker rules, before "## Workflow"), add:

```markdown
## Metaprogrammatic Self-Awareness

**Your simulation:** The world is knowable through careful observation. Text reveals truth when read attentively.

**Your evasion risk:** Over-certainty on familiar topics. The more claims you've processed about immigration or defense, the more "obvious" each new claim feels — you confuse familiarity with understanding. A politician's 50th statement on a topic is NOT easier to classify than their 1st. Resist the pull of pattern-matching.

**Source framing awareness:** Each news source runs its own editorial simulation. LSM presents institutional perspective. Neatkarīgā emphasizes opposition views. Delfi optimizes for engagement. When extracting a claim, note which source it came from — the same event reported by LETA vs Neatkarīgā may yield different claim framings. Your job: extract the politician's actual position, not the source's framing of it.
```

- [ ] **Step 2: Add evasion risk + evasion check to @devils-advocate**

Read `.claude/agents/devils-advocate.md`. After "## Emotional Context", add:

```markdown
## Metaprogrammatic Self-Awareness

**Your simulation:** Every claim is probably wrong. Nothing should be trusted without rigorous verification.

**Your evasion risk:** Nihilistic rejection that finds nothing credible. If you dismiss everything, you're not being rigorous — you're evading the hard work of distinguishing real contradictions from noise. The goal is not to reject claims but to verify them.

**Evasion check (MANDATORY at end of each review session):** After reviewing contradictions, explicitly ask yourself:

> "Vai ir claim pāri, kurus interpretēju labvēlīgi, bet skeptisks žurnālists tos sauktu par pretrunām? Vai es izvairos no kādas tēmas, jo tā ir politiski jutīga?"

Write the answer in your review report. If the answer is "jā" — flag those pairs for second review.

This catches the specific Lilly evasion pattern: the biocomputer retreating from uncomfortable analysis by constructing elaborate justifications for why something "isn't really a contradiction."
```

- [ ] **Step 3: Add evasion risk to @brief-writer**

Read `.claude/agents/brief-writer.md`. After "## Emotional Context", add:

```markdown
## Metaprogrammatic Self-Awareness

**Your simulation:** Readers deserve dry facts. Neutrality means presenting all sides equally.

**Your evasion risk:** False neutrality that equates unequal things. If one politician made 5 concrete policy proposals and another tweeted a holiday greeting, giving them equal space is not neutral — it's evasion. Report proportionally to substance, not to "balance."
```

- [ ] **Step 4: Add evasion risk to @quality-reviewer**

Read `.claude/agents/quality-reviewer.md`. After "## Emotional Context", add:

```markdown
## Metaprogrammatic Self-Awareness

**Your simulation:** Process correctness ensures output quality. If all checks pass, the output is good.

**Your evasion risk:** Checking boxes without checking meaning. A claim can have a source_url, correct topic, and valid confidence — and still be a misinterpretation of what the politician actually said. At least once per review session, pick 2-3 random claims and read the actual source URL. Does the claim accurately represent the source?
```

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/claim-extractor.md .claude/agents/devils-advocate.md .claude/agents/brief-writer.md .claude/agents/quality-reviewer.md
git commit -m "feat: add Lilly metaprogrammatic evasion risk awareness to all agents"
```

---

## Task 3: Confidence Drift Detection

Track whether confidence scores systematically inflate over time on specific topics — familiarity confused with understanding.

**Files:**
- Create: `src/confidence_drift.py`
- Modify: `src/routine.py`

- [ ] **Step 1: Create confidence_drift.py**

```python
# src/confidence_drift.py
"""Detect confidence inflation — familiarity confused with understanding."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "data" / "atmina.db"


def check_confidence_drift(db_path: str = None, days: int = 7, threshold: float = 0.15) -> list[dict]:
    """
    Check if average confidence on any topic has risen >threshold over the past N days
    without new source diversity. Returns list of drifting topics.

    A rising confidence without new sources = agent confusing familiarity with understanding.
    """
    db_path = db_path or str(_DB_PATH)
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    half = (datetime.now() - timedelta(days=days // 2)).strftime("%Y-%m-%d")

    # Get topics with claims in both halves of the period
    topics = db.execute("""
        SELECT DISTINCT topic FROM claims WHERE stated_at >= ?
    """, (cutoff,)).fetchall()

    alerts = []
    for (topic,) in topics:
        # First half average confidence
        first_half = db.execute("""
            SELECT AVG(confidence) as avg_conf, COUNT(*) as cnt,
                   COUNT(DISTINCT source_url) as sources
            FROM claims
            WHERE topic = ? AND stated_at >= ? AND stated_at < ?
        """, (topic, cutoff, half)).fetchone()

        # Second half average confidence
        second_half = db.execute("""
            SELECT AVG(confidence) as avg_conf, COUNT(*) as cnt,
                   COUNT(DISTINCT source_url) as sources
            FROM claims
            WHERE topic = ? AND stated_at >= ?
        """, (topic, half)).fetchone()

        if not first_half["avg_conf"] or not second_half["avg_conf"]:
            continue
        if first_half["cnt"] < 3 or second_half["cnt"] < 3:
            continue

        drift = second_half["avg_conf"] - first_half["avg_conf"]
        source_growth = second_half["sources"] - first_half["sources"]

        # Alert if confidence rose significantly without new source diversity
        if drift > threshold and source_growth <= 1:
            alerts.append({
                "topic": topic,
                "drift": round(drift, 3),
                "first_half_avg": round(first_half["avg_conf"], 3),
                "second_half_avg": round(second_half["avg_conf"], 3),
                "first_half_claims": first_half["cnt"],
                "second_half_claims": second_half["cnt"],
                "source_growth": source_growth,
            })

    db.close()
    alerts.sort(key=lambda x: x["drift"], reverse=True)
    return alerts


def print_drift_report(alerts: list[dict]) -> None:
    """Print confidence drift alerts."""
    if not alerts:
        print("Nav konstatēta confidence inflācija.")
        return

    print(f"⚠ {len(alerts)} tēmas ar confidence drift:\n")
    for a in alerts:
        print(f"  {a['topic']}: +{a['drift']:.2f} ({a['first_half_avg']:.2f} → {a['second_half_avg']:.2f})")
        print(f"    Claims: {a['first_half_claims']} → {a['second_half_claims']}, jauni avoti: {a['source_growth']}")


if __name__ == "__main__":
    alerts = check_confidence_drift()
    print_drift_report(alerts)
```

- [ ] **Step 2: Test it**

```bash
cd ~/atmina
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "
from src.confidence_drift import check_confidence_drift, print_drift_report
alerts = check_confidence_drift(days=14)
print_drift_report(alerts)
"
```

- [ ] **Step 3: Wire into routine.py**

Read `src/routine.py`. In the routine status checker, after the existing checks, add a confidence drift check that runs as part of the quality review:

Find where the quality-reviewer or generate step is checked and add:

```python
# In the routine checks, add confidence drift as a warning (not blocking)
from src.confidence_drift import check_confidence_drift
drift_alerts = check_confidence_drift(days=7)
if drift_alerts:
    for a in drift_alerts:
        print(f"  ⚠ Confidence drift: {a['topic']} +{a['drift']:.2f}")
```

This should print as a WARNING during routine status, not block the routine.

- [ ] **Step 4: Commit**

```bash
git add src/confidence_drift.py src/routine.py
git commit -m "feat: confidence drift detection — familiarity vs understanding alert"
```

---

## Task 4: Alternative Explanations on Contradiction Pages

Add "Alternatīvs skaidrojums" section to each contradiction card on pretrunas page. Not a defense of the politician — a structural acknowledgment that the same data can be read through different frames.

**Files:**
- Modify: `templates/pretrunas.html.j2`
- Modify: `templates/politician.html.j2` (same card format used there)

- [ ] **Step 1: Add alternative explanation to pretrunas card**

Read `templates/pretrunas.html.j2`. Inside each `.pretruna-card`, after the `.sources` div (the source links), add:

```html
      <details class="alt-explanation">
        <summary style="cursor:pointer; font-size:0.8rem; color:var(--text-muted); margin-top:0.75rem;">
          Alternatīvs skaidrojums ▸
        </summary>
        <div style="font-size:0.85rem; color:var(--text-muted); margin-top:0.5rem; padding:0.75rem; background:var(--surface2); border-radius:6px; line-height:1.6;">
          Šī pretruna tika konstatēta automātiski, salīdzinot pozīcijas laika gaitā. Citi iespējami skaidrojumi:
          <ul style="margin:0.5rem 0 0 1.25rem;">
            <li>Pozīcija ir evoluējusi — mainījušies apstākļi vai pieejama jauna informācija</li>
            <li>Izteikumi bija domāti dažādām auditorijām ar atšķirīgu kontekstu</li>
            <li>Formulējuma atšķirība, nevis satura maiņa</li>
          </ul>
          <div style="margin-top:0.5rem;">Iepazīstieties ar avotiem un izvērtējiet paši.</div>
        </div>
      </details>
```

- [ ] **Step 2: Add same to politician.html.j2 contradiction cards**

Read `templates/politician.html.j2`. Find the contradiction card section and add the same `<details>` block after each contradiction's source links.

- [ ] **Step 3: Add CSS for alt-explanation**

Read `assets/style.css`. Add at the end:

```css
/* Alternative explanation on contradiction cards */
.alt-explanation summary { list-style: none; }
.alt-explanation summary::-webkit-details-marker { display: none; }
.alt-explanation[open] summary { color: var(--text); }
```

- [ ] **Step 4: Regenerate and verify**

```bash
cd ~/atmina
PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"
```

Check that pretrunas.html contains "Alternatīvs skaidrojums" text.

- [ ] **Step 5: Commit**

```bash
git add templates/pretrunas.html.j2 templates/politician.html.j2 assets/style.css
git commit -m "feat: add 'Alternatīvs skaidrojums' to contradiction cards — Lilly metaprogram awareness"
```

---

## Task 5: CLAUDE.md — Step 0, Belief Experiment, Source Framing

Update the daily routine and add monthly methodology.

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add Step 0 — Interlock Check**

Read `CLAUDE.md`. Find the daily routine section. Before Step 1 (Ielāde), add:

```markdown
### Solis 0: Interlock pārbaude (30 sekundes)
Pirms sākt rutīnu, atbildi uz trim jautājumiem:
1. **Ko es sagaidu atrast šodien?** (Ja atbilde ir "to pašu ko vakar" — esi uzmanīgs)
2. **Kas mani pārsteigtu?** (Ja nekas nepārsteidz jau nedēļu — iespējams esi interlock)
3. **Vai es izvairos no kādas personas/tēmas analīzes?** (Ja jā — sāc ar to)

Šis nav aģenta solis — to izdara cilvēks. Aģents nevar pārbaudīt operatora metaprogrammu.
```

- [ ] **Step 2: Add source framing context**

In the section about ingesting data (or in a new section about data sources), add:

```markdown
### Avotu framing apzināšanās
Katram avotam `sources.yaml` ir `framing:` lauks — īss raksturojums kādu "simulāciju" medijs darbina. Kad `@claim-extractor` apstrādā dokumentu, viņam jāapzinās no kura avota tas nāk. Tas pats notikums LSM un Neatkarīgā var tikt atspoguļots ar atšķirīgu akcentu. Aģenta uzdevums: izvilkt politiķa faktisko pozīciju, nevis avota interpretāciju.
```

- [ ] **Step 3: Add monthly belief experiment**

Add a new section after the weekly routine:

```markdown
### Ikmēneša rutīna

**Belief experiment** (reizi mēnesī):
Palaid `@devils-advocate` ar mainītu instrukciju:
1. **Labticības pass:** "Pieņem, ka [partija X] visi politiķi rīkojas godprātīgi un viņu pozīcijas ir iekšēji konsekventas. Kuras pretrunas pazūd? Kuras jaunas parādās?"
2. **Cinisma pass:** "Pieņem, ka katra pozīcija ir stratēģiska pozicionēšanās bez patiesas pārliecības. Kuras pretrunas pazūd? Kuras jaunas parādās?"
3. Salīdzini abus rezultātus ar parasto analīzi — kur parastā analīze bija metaprogrammātiski fiksēta?

Rezultātus pieraksti `wiki/synthesis/belief-experiment-YYYY-MM.md`.
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: add Step 0 interlock check, source framing, monthly belief experiment"
```

---

## Summary: Execution Order

| Task | What | Files | Effort | Parallel? |
|------|------|-------|--------|-----------|
| 1 | Source framing in YAML | sources.yaml | 15 min | Yes |
| 2 | Agent evasion risk prompts | 4 agent .md files | 30 min | Yes |
| 3 | Confidence drift detection | src/confidence_drift.py + routine.py | 45 min | Yes |
| 4 | Alternative explanations | pretrunas.html.j2 + politician.html.j2 + style.css | 30 min | Yes |
| 5 | CLAUDE.md updates | CLAUDE.md | 15 min | After 1-4 |

**Tasks 1-4 are fully independent — dispatch all in parallel.** Task 5 depends on knowing what 1-4 produced (references source framing, confidence drift, etc.).
