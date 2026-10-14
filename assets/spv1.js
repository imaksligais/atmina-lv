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

  // Trigerī rāda opcijas etiķeti («Nostāju konflikts»), ne DB vērtību.
  const typeLabel = v => {
    const o = [...document.querySelectorAll('#type-select .multi-select-option')]
      .find(el => el.dataset.value === v);
    return o ? o.textContent.trim() : v;
  };
  atminaMultiSelect({ root: 'type-select', selected: selectedTypes, display: typeLabel,
    allLabel: 'Visi tipi', pluralLabel: 'tipi izvēlēti', onChange: applyFilters });
  atminaMultiSelect({ root: 'party-select', selected: selectedParties,
    allLabel: 'Visas partijas', pluralLabel: 'partijas izvēlētas', onChange: applyFilters });
  atminaMultiSelect({ root: 'person-select', selected: selectedPersons,
    allLabel: 'Visas personas', pluralLabel: 'personas izvēlētas', onChange: applyFilters });
})();
