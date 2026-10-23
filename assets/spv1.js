(function() {
  let selectedTypes = new Set();
  let selectedParties = new Set();
  let selectedPersons = new Set();
  const cards = document.querySelectorAll('#tensions-grid .card');

  // «Rāda N no M …» + tukšais stāvoklis — kopīgais window.atminaShowCount
  // (assets/sgv1.js; abi `defer`, sgv1 pirmais).
  const showCount = (shown, countId, emptyId, noun) =>
    window.atminaShowCount(countId, emptyId, shown, cards.length, noun);

  function applyFilters() {
    let shown = 0;
    cards.forEach(card => {
      const matchType = selectedTypes.size === 0 || selectedTypes.has(card.dataset.type);
      // Partija atbilst autoram VAI adresātam (2026-10-18).
      const matchParty = selectedParties.size === 0
        || selectedParties.has(card.dataset.sourceParty)
        || selectedParties.has(card.dataset.targetParty);
      let matchPerson = selectedPersons.size === 0;
      if (!matchPerson) {
        matchPerson = selectedPersons.has(card.dataset.sourcePerson) || selectedPersons.has(card.dataset.targetPerson);
      }
      const match = matchType && matchParty && matchPerson;
      card.style.display = match ? '' : 'none';
      if (match) shown++;
    });
    showCount(shown, 'tensions-count', 'tensions-empty', 'spriedzēm');
    syncUrl();
  }

  // URL parametri: tie paši nosaukumi un komatu formāts kā sav1.js::syncUrl.
  function syncUrl() {
    const params = new URLSearchParams();
    if (selectedTypes.size > 0) params.set('type', [...selectedTypes].join(','));
    if (selectedParties.size > 0) params.set('party', [...selectedParties].join(','));
    if (selectedPersons.size > 0) params.set('person', [...selectedPersons].join(','));
    const qs = params.toString();
    history.replaceState(null, '', window.location.pathname + (qs ? '?' + qs : '') + window.location.hash);
  }

  // Trigerī rāda opcijas etiķeti («Nostāju konflikts»), ne DB vērtību.
  const typeLabel = v => {
    const o = [...document.querySelectorAll('#type-select .multi-select-option')]
      .find(el => el.dataset.value === v);
    return o ? o.textContent.trim() : v;
  };
  const typeMs = atminaMultiSelect({ root: 'type-select', selected: selectedTypes, display: typeLabel,
    allLabel: 'Visi tipi', pluralLabel: 'tipi izvēlēti', onChange: applyFilters });
  const partyMs = atminaMultiSelect({ root: 'party-select', selected: selectedParties,
    allLabel: 'Visas partijas', pluralLabel: 'partijas izvēlētas', onChange: applyFilters });
  const personMs = atminaMultiSelect({ root: 'person-select', selected: selectedPersons,
    allLabel: 'Visas personas', pluralLabel: 'personas izvēlētas', onChange: applyFilters });

  // Nolasa filtrus no adreses. Paturam tikai vērtības, kurām lapā ir opcija:
  // nezināma vērtība (veca saite) tiek ignorēta, nevis dod 0 kartīšu.
  function applyFromUrl() {
    const params = new URLSearchParams(window.location.search);
    let any = false;
    [['type', typeMs], ['party', partyMs], ['person', personMs]].forEach(([name, ms]) => {
      const val = params.get(name);
      if (!val || !ms) return;
      const wanted = new Set(val.split(',').map(v => v.trim()).filter(Boolean));
      const known = [...ms.options].map(o => o.dataset.value).filter(v => wanted.has(v));
      if (known.length) { ms.setSelection(known); any = true; }
    });
    if (any) applyFilters();
    else showCount(cards.length, 'tensions-count', 'tensions-empty', 'spriedzēm');
  }

  applyFromUrl();
})();
