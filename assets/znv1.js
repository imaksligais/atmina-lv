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

  // Pieminēto filtram etiķetē noņem prefiksu (party:/person:).
  const stripPrefix = v => v.replace(/^(party|person):/, '');

  atminaMultiSelect({ root: 'source-select', selected: selectedSources,
    allLabel: 'Visi avoti', pluralLabel: 'avoti izvēlēti', onChange: applyFilters, display: stripPrefix });
  atminaMultiSelect({ root: 'topic-select', selected: selectedTopics,
    allLabel: 'Visas tēmas', pluralLabel: 'tēmas izvēlētas', onChange: applyFilters, display: stripPrefix });
  atminaMultiSelect({ root: 'mentioned-person-select', selected: selectedPersons,
    allLabel: 'Persona', pluralLabel: 'personas izvēlētas', onChange: applyFilters, display: stripPrefix });
  atminaMultiSelect({ root: 'mentioned-party-select', selected: selectedParties,
    allLabel: 'Partija', pluralLabel: 'partijas izvēlētas', onChange: applyFilters, display: stripPrefix });

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
})();
