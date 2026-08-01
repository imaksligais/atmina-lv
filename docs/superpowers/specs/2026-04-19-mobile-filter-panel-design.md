# Mobile filter panel — Pozīcijas & X

**Datums:** 2026-04-19
**Skartās lapas:** `/pozicijas.html`, `/x.html`
**Breakpoint:** `@media (max-width: 900px)` (atbilst esošajam grid-collapse breakpoint)

## Problēma

Uz mobile abās lapās pirmais skatītais saturs ir filtri (`pzv1-aside` / `xv1-aside` + `xv1-filters`), nevis saraksts/feed. Lietotājam, kas atver lapu telefonā, jāskrollē ~6–10 rindas pirms redz galveno saturu.

## Mērķis

Uz mobile: saturs sākas uzreiz zem galvenes. Filtri paslēpti zem vienas `Filtri (N)` pogas + aktīvo filtru chip-rindas. Desktop uzvedība nemainās.

## Uzvedība

### Mobile (≤900px)

Zem esošās galvenes parādās `pzv1-mobile-filterbar` / `xv1-mobile-filterbar`:

```
[Filtri (0)]                                     ← bez filtriem
[Filtri (2)]  [Tēma: Drošība ✕]  [JV ✕]          ← ar filtriem
[Filtri (3)]  [Tips: Ieraksti ✕]  [Kariņš ✕]  [JV ✕]  Notīrīt visu   ← ≥2 filtri
```

Saraksts/feed sākas uzreiz zem šīs rindas.

**Chip bar redzamība:** tikai kad ≥1 aktīvs filtrs (`hidden` atribūts pret containeru).
**"Notīrīt visu":** parādās no 2+ aktīviem filtriem.
**Klikšķis uz `Filtri`:** atklāj filtru zonu inline accordion veidā (Pozīcijas: `pzv1-aside`; X: `xv1-aside` + `xv1-ticker-bar`). Bez overlay, bez body-lock, bez height animācijas — instant snap.
**Klikšķis uz chip `✕`:** noņem to vienu filtru, paneli neatver.
**Klikšķis uz `Notīrīt visu`:** noņem visus filtrus.

### Desktop (>900px)

Nav izmaiņu. `aside` paliek kā kreisā kolonna. `pzv1-mobile-filterbar` un `xv1-mobile-filterbar` — `display: none`.

### X tab panel saturs (atvērtā stāvoklī)

Kārtība = DOM kārtība, zero DOM izmaiņu pieeja:

1. Pieminētākie · pēdējās 7 dienas (no `xv1-aside`)
2. Tēmas · pēdējās 7 dienas (no `xv1-aside`)
3. Tipa tabi (Visi / Ieraksti / Pieminējumi) (no `xv1-ticker-bar`)
4. Persona dropdown (no `xv1-ticker-bar`)
5. Partija dropdown (no `xv1-ticker-bar`)

Stats pirms filtriem nav piekāpšanās — tas dod kontekstualizāciju ("Kariņš, 47 pieminējumi") pirms lietotājs izlemj, ko filtrēt. Visi pieci ir klikšķināmi/interaktīvi un iedarbojas uz to pašu feed zemāk.

## Tehniskā realizācija

### Arhitektūras princips

**Nulle DOM restrukturizācijas.** Esošais HTML templates struktūra nemainās — mobile uzvedība pievienota kā neatkarīgs slānis (jauni elementi + jauns atribūts + jauni CSS noteikumi iekš `@media`). Desktop koda ceļš paliek bit-identical. Šī pieeja izvēlēta apzināti pār DOM wrapping variantu, jo: (1) `xv1-filters` semantiski pieder `xv1-main` kā feed toolbar, (2) desktop/mobile ir atsevišķi UX un viņiem nav jādala struktūra, (3) progressive enhancement ir vieglāk uzturams nekā kopīga DOM.

### Markup delta

**`templates/pozicijas.html.j2`** — viena lieta pievienota, nekas nepārvietots:

Starp `<header class="pzv1-header">...</header>` un `<div class="pzv1-grid">` ievietot:

```html
<div class="pzv1-mobile-filterbar">
  <button class="pzv1-mobile-toggle" type="button" aria-expanded="false">
    Filtri <span class="pzv1-mobile-count">(0)</span>
  </button>
  <div class="pzv1-mobile-chips" hidden></div>
</div>
```

Uz `<div class="pzv1-grid">` pievieno atribūtu `data-mobile-filter-open="false"`. Tas ir *vienīgais* grozījums esošā markupā. `<aside class="pzv1-aside">` un viss tā saturs paliek neskarts.

**`templates/x.html.j2`** — tas pats pattern:

Pirms `<div class="xv1-grid">` ievieto `xv1-mobile-filterbar` (toggle + chip bar). Uz `<div class="xv1-grid">` pievieno `data-mobile-filter-open="false"`. Esošie `<aside class="xv1-aside">`, `<div class="xv1-ticker-bar">`, `<div class="xv1-tabs">`, `<div class="xv1-filters">` **paliek tieši kur ir**. Nekas nepārvietojas.

### CSS

Visi jaunie stili ir pilnīgi jaunas selektoru rindas — neviena esošā deklarācija netiek modificēta.

```css
/* default (desktop) — jaunie elementi paslēpti */
.pzv1-mobile-filterbar,
.xv1-mobile-filterbar {
  display: none;
}

@media (max-width: 900px) {
  /* mobile filter bar redzams */
  .pzv1-mobile-filterbar,
  .xv1-mobile-filterbar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    margin: 16px 0 12px;
  }
  .pzv1-mobile-toggle,
  .xv1-mobile-toggle {
    /* border, padding, font — konsistenti ar esošajiem pzv1-rail-row stiliem */
  }
  .pzv1-mobile-chips,
  .xv1-mobile-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }
  /* native [hidden] atribūts jau slēpj; override nav vajadzīgs */

  /* paneļa atverēs/aizvēršana caur data atribūtu uz grid */
  .pzv1-grid[data-mobile-filter-open="false"] .pzv1-aside { display: none; }
  .xv1-grid[data-mobile-filter-open="false"] .xv1-aside { display: none; }
  .xv1-grid[data-mobile-filter-open="false"] .xv1-ticker-bar { display: none; }
}
```

Bez height transition — instant snap. Desktop (>900px): `xv1-grid[data-mobile-filter-open]` selektors esošajai CSS nav saistošs, jo viņu ignorē tie paši stili, kas strādā šobrīd.

### JS

**`assets/pzv1.js`** — jauna funkcija `renderMobileFilterState()`:

```
function renderMobileFilterState() {
  const DEFAULT_VALUES = new Set(['visas', 'Visas', 'visi']);
  const actives = [];
  document.querySelectorAll('.pzv1-rail-row[data-axis].is-active').forEach(btn => {
    const value = btn.dataset.value;
    if (DEFAULT_VALUES.has(value)) return;
    const label = btn.querySelector('.pzv1-rail-label').textContent;
    actives.push({ axis: btn.dataset.axis, value, label });
  });
  // Update .pzv1-mobile-count → "(N)"
  // Rebuild #pzv1-mobile-chips contents:
  //   - one .pzv1-chip button per active
  //   - if actives.length >= 2: append .pzv1-mobile-clearall button
  // Toggle [hidden] on #pzv1-mobile-chips based on actives.length === 0
}
```

**Hook points:** katrā vietā, kur tiek pievienota/noņemta `.is-active` klase rail-row elementiem (piem., `pzv1.js:272` ap `document.querySelectorAll(".pzv1-rail-row").forEach(b => ...)`), pēc toggling pievienojam `renderMobileFilterState()` zvanu. Sākotnēji — `document.addEventListener('DOMContentLoaded', renderMobileFilterState)`.

**Chip `✕` klikšķa handler:**
```
chipsContainer.addEventListener('click', (e) => {
  const chip = e.target.closest('.pzv1-chip');
  if (!chip) return;
  const axis = chip.dataset.axis;
  const defaultBtn = document.querySelector(
    `.pzv1-rail-row[data-axis="${axis}"][data-value="visas"], ` +
    `.pzv1-rail-row[data-axis="${axis}"][data-value="Visas"]`
  );
  defaultBtn?.click();  // izmanto esošo filter reset path
});
```

**`Notīrīt visu` handler:** iteratīvi izsauc `defaultBtn.click()` pa visām asīm.

**Toggle pogas handler:**
```
toggleBtn.addEventListener('click', () => {
  const grid = document.querySelector('.pzv1-grid');
  const isOpen = grid.dataset.mobileFilterOpen === 'true';
  grid.dataset.mobileFilterOpen = String(!isOpen);
  toggleBtn.setAttribute('aria-expanded', String(!isOpen));
});
```

Stāvoklis glabājas uz grid elementa (nevis uz aside), jo X tabā tas pats atribūts kontrolē gan `xv1-aside`, gan `xv1-ticker-bar` vienlaicīgu redzamību. Viens stāvokļa avots, divi DOM patērētāji caur CSS.

**`assets/x-v1.js`** — tas pats pattern, bet ar trim chip avotiem:
- Rail-row klikšķi no `xv1-aside` (Pieminētākie / Tēmas)
- Dropdown opciju aktivācijas no `xv1-filters` (persona, partija)
- Type tab aktivācijas (Visi / Ieraksti / Pieminējumi)

Ne-default tipa tabs (`post`, `mention`) ģenerē chip `Tips: Ieraksti ✕` vai `Tips: Pieminējumi ✕`. Default (`Visi`) chip nav.

### Pieejamība

- Toggle poga: `aria-expanded="false|true"`. `aria-controls` izlaists apzināti, jo kontrolētā zona uz X tab ir divi nesaistīti DOM elementi (`xv1-aside` + `xv1-ticker-bar`) — `aria-expanded` viens pats skaidri apzīmē disclosure pattern un screen readers to saprot.
- Chip pogas: `aria-label="Noņemt filtru: <axis>: <value>"`.
- Chip bar kad tukšs: `hidden` atribūts → screen reader to neziņo.
- Fokuss: pēc chip `✕` klikšķa paliek uz chip_`parent` (chip tiek noņemts no DOM, fokuss pārvietojas uz body — pieņemams, jo lietotājs tipiski redz layout izmaiņas).
- Nav focus trap (nav modal).

## Verifikācija

1. `python -c "from src.generate import generate_public_site; generate_public_site()"`
2. `python serve.py`
3. Chrome DevTools responsive mode → 375×812 (iPhone SE). Pārbauda:
   - Feed/saraksts sākas zem `Filtri (0)` pogas.
   - Chip bar tukšā stāvoklī layout'ā neeksistē (`hidden` atribūts).
   - Filtra aktivācija iekš paneļa → chip parādās + count uzskaita.
   - Chip `✕` → filtrs noņemts, saraksts atjaunots, count samazināts.
   - `Notīrīt visu` — parādās no 2+ chipiem, noņem visus.
   - Keyboard: Tab uz toggle → Enter atver → Tab iekšā panelī → filtrs → Shift+Tab → Enter aizver.
4. Resize uz 1200px — chip bar + toggle pazūd, aside atgriežas kā kreisā kolonna, filter state saglabāts.
5. `python -m pytest tests/ -v` — jāpaliek zaļam.

## Fāzēta realizācija

| Fāze | Faili | Pārbauda |
|---|---|---|
| 1 — Pozīcijas | `templates/pozicijas.html.j2`, `assets/style.css`, `assets/pzv1.js` | Manuāls browser test + pytest |
| 2 — X tab | `templates/x.html.j2`, `assets/style.css` (append), `assets/x-v1.js` | Manuāls browser test + pytest |

Fāze 1 tiek pilnībā pabeigta un apstiprināta pirms fāzes 2.

## Scope disciplīna (YAGNI)

**Izslēgts no šī spec:**
- Height animācija pie paneļa atvēršanas.
- Swipe-to-close gesti.
- Bottom sheet / modal variants.
- Filter state sync uz URL (esošā uzvedība saglabājas).
- Desktop filter panelis — nav problēma.
- Blog / Partiju / Personas / pārējās lapas — citas struktūras, ārpus šī uzdevuma.
