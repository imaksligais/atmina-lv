# "Par mums" Page Redesign

## Context

The about page (templates/about.html.j2) exists but is dead — not linked from nav, not rendered by generate.py. Needs full rewrite as a credible explanation of what atmina.lv is, how it works, and what it tracks.

## Audiences

- Regular citizen (first visit): understand what this is
- Journalist/researcher: methodology, data credibility
- Potential client: value of agents.atmina.lv
- Politician/party: how their data is processed

## Page Structure

### 1. Hero
- Headline: "Vai darbi sakrit ar vardiem?"
- Subline: atmina.lv ir politiska atmina — track what politicians say, compare with what they do

### 2. Pipeline (4 visual steps)
Avoti -> MI agenti -> Cilveka parbaude -> Publicesana

- **Avoti**: mediji (XX portali), X/Twitter, Saeima (balsojumi, stenogrammas), publiskie dati (KNAB deklaracijas, velesanu finanses, valsts statistika)
- **MI agenti**: extract claims, find contradictions, analyze patterns
- **Cilveka parbaude**: every analysis reviewed before publishing
- **Publicesana**: every record links to original source

### 3. What We Track (5 cards with live stats from DB)
- Pozicijas — what politicians say on specific topics
- Pretrunas — when words don't match previous positions or votes
- Balsojumi — Saeima voting records
- Saites — tensions and attacks between politicians
- Zinas — aggregated from sources

### 4. Methodology (collapsible accordions)
- Confidence scores (0.0-1.0)
- 26 thematic categories
- Deduplication (embedding + simhash)
- Source coverage and limitations

### 5. Disclaimers
- Selective coverage
- AI can make mistakes
- Check original source
- Confidence != truth

### 6. CTA Banner
"MI politiska izlukosana jusu organizacijai" -> agents.atmina.lv

### 7. Footer link
Add "Par mums" link to footer in base.html.j2 (not in nav tabs).

## Implementation

- Rewrite templates/about.html.j2
- Add render call in src/generate.py (pass live stats from DB)
- Add footer link in templates/base.html.j2
- Style: reuse existing card/grid/section classes from assets/style.css
