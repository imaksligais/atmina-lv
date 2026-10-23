// lkv1.js — pamatlikumu indeksa filtri (izcelts no templates/likumi-index.html.j2
// inline skripta stingrās CSP dēļ). Ielādēts ar defer PĒC ms-a11y.js un msv1.js
// (abi sinhroni) — lieto window.atminaMultiSelect; defer garantē, ka DOM ir gatavs.
//
// Deleģācija (aizstāj noņemto oninput atribūtu):
//   • #law-search (input) → window.applyLawsFilters
// window.filterOptions vairs netiek definēts — meklēšanas filtrēšanu pārņem
// assets/ms-a11y.js deleģētais 'input' klausītājs.
(function() {
  const selectedTopics = new Set();
  let hasFilter = '';  // '' | 'yes' | 'no' — «Ar / Bez likumprojektiem» (2026-10-20)

  // Garumzīmju locīšana — kopīgā window.atminaFold (assets/sgv1.js, defer, pirms
  // šī faila); abas puses locītas («velesanu» atrod «vēlēšanu»).
  function fold(s) { return window.atminaFold ? window.atminaFold(s) : String(s).toLowerCase(); }

  window.applyLawsFilters = function() {
    const q = fold(document.getElementById('law-search').value || '');
    const cards = document.querySelectorAll('#laws-grid .bill-card');
    let shown = 0;
    cards.forEach(function(c) {
      const matchTopic = selectedTopics.size === 0 || selectedTopics.has(c.dataset.topic);
      const matchQ = !q || fold(c.dataset.title).indexOf(q) !== -1;
      const matchHas = !hasFilter || c.dataset.has === hasFilter;
      const ok = matchTopic && matchQ && matchHas;
      c.style.display = ok ? '' : 'none';
      if (ok) shown++;
    });
    const count = document.getElementById('laws-count');
    if (count) count.textContent = 'Rāda ' + shown + ' no ' + cards.length;
    const empty = document.getElementById('laws-empty');
    if (empty) empty.hidden = shown !== 0;
  };

  document.querySelectorAll('.likumi-has-bills .link-filter-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      hasFilter = btn.dataset.has;
      document.querySelectorAll('.likumi-has-bills .link-filter-btn').forEach(function(b) {
        const on = b === btn;
        b.classList.toggle('active', on);
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
      window.applyLawsFilters();
    });
  });

  // Tēmu multi-select — kopīgais assets/msv1.js (ielādēts sinhroni pirms šī
  // faila); atvēršana, atlase, notīrīšana, etiķete un klikšķis-ārpusē ir tur.
  window.atminaMultiSelect({
    root: 'law-topic-select',
    selected: selectedTopics,
    allLabel: 'Visas tēmas',
    pluralLabel: 'tēmas izvēlētas',
    onChange: window.applyLawsFilters,
  });

  // Meklēšana: #law-search ievade → applyLawsFilters (aizstāj noņemto oninput).
  const lawSearch = document.getElementById('law-search');
  if (lawSearch) lawSearch.addEventListener('input', function() {
    window.applyLawsFilters();
  });
})();
