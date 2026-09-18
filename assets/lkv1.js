// lkv1.js — pamatlikumu indeksa filtri (izcelts no templates/likumi-index.html.j2
// inline skripta stingrās CSP dēļ). Ielādēts ar defer PĒC ms-a11y.js — nav
// atkarīgs no cita skripta window.* globāļa, tikai no DOM, tāpēc secība nav
// kritiska; defer garantē, ka DOM ir gatavs.
//
// Deleģācija (aizstāj noņemto oninput atribūtu):
//   • #law-search (input) → window.applyLawsFilters
// window.filterOptions vairs netiek definēts — meklēšanas filtrēšanu pārņem
// assets/ms-a11y.js deleģētais 'input' klausītājs.
(function() {
  const selectedTopics = new Set();

  window.applyLawsFilters = function() {
    const q = (document.getElementById('law-search').value || '').toLowerCase();
    document.querySelectorAll('#laws-grid .bill-card').forEach(function(c) {
      const matchTopic = selectedTopics.size === 0 || selectedTopics.has(c.dataset.topic);
      const matchQ = !q || c.dataset.title.indexOf(q) !== -1;
      c.style.display = (matchTopic && matchQ) ? '' : 'none';
    });
  };

  const select = document.getElementById('law-topic-select');
  const trigger = document.getElementById('law-topic-trigger');
  const label = trigger.querySelector('span');

  trigger.addEventListener('click', e => {
    e.stopPropagation();
    select.classList.toggle('open');
    const search = select.querySelector('.multi-select-search');
    if (search && select.classList.contains('open')) setTimeout(() => search.focus(), 50);
  });

  select.querySelectorAll('.multi-select-option').forEach(opt => {
    opt.addEventListener('click', e => {
      e.stopPropagation();
      const val = opt.dataset.value;
      if (selectedTopics.has(val)) { selectedTopics.delete(val); opt.classList.remove('selected'); }
      else { selectedTopics.add(val); opt.classList.add('selected'); }
      updateLabel();
      window.applyLawsFilters();
    });
  });

  select.querySelector('.multi-select-clear').addEventListener('click', e => {
    e.stopPropagation();
    selectedTopics.clear();
    select.querySelectorAll('.multi-select-option').forEach(o => o.classList.remove('selected'));
    updateLabel();
    window.applyLawsFilters();
  });

  function updateLabel() {
    if (selectedTopics.size === 0) { label.textContent = 'Visas tēmas'; trigger.classList.remove('has-selection'); }
    else if (selectedTopics.size <= 2) { label.textContent = [...selectedTopics].join(', '); trigger.classList.add('has-selection'); }
    else { label.textContent = selectedTopics.size + ' tēmas izvēlētas'; trigger.classList.add('has-selection'); }
  }

  document.addEventListener('click', e => {
    if (!select.contains(e.target)) select.classList.remove('open');
  });

  // Meklēšana: #law-search ievade → applyLawsFilters (aizstāj noņemto oninput).
  const lawSearch = document.getElementById('law-search');
  if (lawSearch) lawSearch.addEventListener('input', function() {
    window.applyLawsFilters();
  });
})();
