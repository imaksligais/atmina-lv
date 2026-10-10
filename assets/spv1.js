(function() {
  let selectedTypes = new Set();
  let selectedParties = new Set();
  let selectedPersons = new Set();
  const cards = document.querySelectorAll('#tensions-grid .card');

  function applyFilters() {
    cards.forEach(card => {
      const matchType = selectedTypes.size === 0 || selectedTypes.has(card.dataset.type);
      const matchParty = selectedParties.size === 0 || selectedParties.has(card.dataset.party);
      let matchPerson = selectedPersons.size === 0;
      if (!matchPerson) {
        matchPerson = selectedPersons.has(card.dataset.sourcePerson) || selectedPersons.has(card.dataset.targetPerson);
      }
      card.style.display = (matchType && matchParty && matchPerson) ? '' : 'none';
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
      else if (selectedSet.size <= 2) { label.textContent = [...selectedSet].join(', '); trigger.classList.add('has-selection'); }
      else { label.textContent = selectedSet.size + ' ' + pluralLabel; trigger.classList.add('has-selection'); }
    }
  }

  setupMultiSelect('type-select', 'type-trigger', selectedTypes, 'Visi tipi', 'tipi izvēlēti');
  setupMultiSelect('party-select', 'party-trigger', selectedParties, 'Visas partijas', 'partijas izvēlētas');
  setupMultiSelect('person-select', 'person-trigger', selectedPersons, 'Visas personas', 'personas izvēlētas');

  document.addEventListener('click', e => {
    document.querySelectorAll('.multi-select.open').forEach(s => {
      if (!s.contains(e.target)) s.classList.remove('open');
    });
  });
})();
