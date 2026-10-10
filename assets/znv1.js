(function() {
  let selectedSources = new Set();
  let selectedTopics = new Set();
  let selectedPersons = new Set();
  let selectedParties = new Set();
  const cards = document.querySelectorAll('#news-list .news-card');

  function applyFilters() {
    cards.forEach(card => {
      const matchSource = selectedSources.size === 0 || selectedSources.has(card.dataset.source);

      let matchTopic = selectedTopics.size === 0;
      if (!matchTopic) {
        const topics = card.dataset.topics || '';
        for (const t of selectedTopics) {
          if (topics.split(',').includes(t)) { matchTopic = true; break; }
        }
      }

      let matchPerson = selectedPersons.size === 0;
      if (!matchPerson) {
        const persons = (card.dataset.persons || '').split('|');
        for (const p of selectedPersons) {
          if (persons.includes(p)) { matchPerson = true; break; }
        }
      }

      let matchParty = selectedParties.size === 0;
      if (!matchParty) {
        const parties = (card.dataset.parties || '').split('|');
        for (const p of selectedParties) {
          if (parties.includes(p)) { matchParty = true; break; }
        }
      }

      card.style.display = (matchSource && matchTopic && matchPerson && matchParty) ? '' : 'none';
    });
  }

  function setupMultiSelect(selectId, triggerId, selectedSet, allLabel, pluralLabel) {
    const select = document.getElementById(selectId);
    const trigger = document.getElementById(triggerId);
    const label = trigger.querySelector('span');

    trigger.addEventListener('click', e => {
      e.stopPropagation();
      document.querySelectorAll('.multi-select.open').forEach(s => {
        if (s.id !== selectId) s.classList.remove('open');
      });
      select.classList.toggle('open');
      const search = select.querySelector('.multi-select-search');
      if (search && select.classList.contains('open')) setTimeout(() => search.focus(), 50);
    });

    select.querySelectorAll('.multi-select-option').forEach(opt => {
      opt.addEventListener('click', e => {
        e.stopPropagation();
        const val = opt.dataset.value;
        if (selectedSet.has(val)) { selectedSet.delete(val); opt.classList.remove('selected'); }
        else { selectedSet.add(val); opt.classList.add('selected'); }
        updateLabel();
        applyFilters();
      });
    });

    select.querySelector('.multi-select-clear').addEventListener('click', e => {
      e.stopPropagation();
      selectedSet.clear();
      select.querySelectorAll('.multi-select-option').forEach(o => o.classList.remove('selected'));
      updateLabel();
      applyFilters();
    });

    function updateLabel() {
      if (selectedSet.size === 0) { label.textContent = allLabel; trigger.classList.remove('has-selection'); }
      else if (selectedSet.size <= 2) {
        // For mentioned filter, strip prefix for display
        const display = [...selectedSet].map(v => v.replace(/^(party|person):/, '')).join(', ');
        label.textContent = display;
        trigger.classList.add('has-selection');
      }
      else { label.textContent = selectedSet.size + ' ' + pluralLabel; trigger.classList.add('has-selection'); }
    }
  }

  setupMultiSelect('source-select', 'source-trigger', selectedSources, 'Visi avoti', 'avoti izvēlēti');
  setupMultiSelect('topic-select', 'topic-trigger', selectedTopics, 'Visas tēmas', 'tēmas izvēlētas');
  setupMultiSelect('mentioned-person-select', 'mentioned-person-trigger', selectedPersons, 'Persona', 'personas izvēlētas');
  setupMultiSelect('mentioned-party-select', 'mentioned-party-trigger', selectedParties, 'Partija', 'partijas izvēlētas');

  // URL param preselection: ?persona=Name
  var urlParams = new URLSearchParams(location.search);
  var preselect = urlParams.get('persona');
  if (preselect) {
    var decoded = decodeURIComponent(preselect);
    selectedPersons.add(decoded);
    var mentionSelect = document.getElementById('mentioned-person-select');
    mentionSelect.querySelectorAll('.multi-select-option').forEach(function(opt) {
      if (opt.dataset.value === decoded) opt.classList.add('selected');
    });
    var mentionTrigger = document.getElementById('mentioned-person-trigger');
    mentionTrigger.querySelector('span').textContent = decoded;
    mentionTrigger.classList.add('has-selection');
    applyFilters();
  }

  document.addEventListener('click', e => {
    document.querySelectorAll('.multi-select.open').forEach(s => {
      if (!s.contains(e.target)) s.classList.remove('open');
    });
  });
})();
