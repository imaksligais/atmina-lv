(function() {
  let activeSeverity = 'all';
  let groupMode = 'chrono';
  let sortMode = 'new';
  const selectedParties = new Set();
  const selectedPersons = new Set();

  const register = document.getElementById('register');
  const rows = [...register.querySelectorAll(':scope > .prv2-row')];
  const registerCount = document.getElementById('register-count');
  const registerEmpty = document.getElementById('register-empty');
  const sevChips = document.getElementById('severity-chips');

  function matchesFilters(el) {
    const matchSev = activeSeverity === 'all' || el.dataset.severity === activeSeverity;
    const matchParty = selectedParties.size === 0 || selectedParties.has(el.dataset.party);
    const matchPerson = selectedPersons.size === 0 || selectedPersons.has(el.dataset.person);
    return matchSev && matchParty && matchPerson;
  }

  function rowVisible(row) {
    return matchesFilters(row);
  }

  function cmpRows(a, b) {
    if (sortMode === 'salience') {
      const d = parseFloat(b.dataset.salience || '0') - parseFloat(a.dataset.salience || '0');
      if (d !== 0) return d;
    }
    const t = (b.dataset.detected || '').localeCompare(a.dataset.detected || '');
    if (t !== 0) return t;
    return parseInt(b.id.replace('pretruna-', '')) - parseInt(a.id.replace('pretruna-', ''));
  }

  function renderRegister() {
    // 1) Atkārtoti izkārto visas rindas plakanai un noņem vecās grupas.
    let visibleCount = 0;
    rows.forEach(r => {
      register.appendChild(r);
      const vis = rowVisible(r);
      r.style.display = vis ? '' : 'none';
      if (vis) visibleCount++;
    });
    register.querySelectorAll(':scope > .prv2-group').forEach(g => g.remove());
    registerCount.textContent = visibleCount === rows.length
      ? '(' + rows.length + ')'
      : '(' + visibleCount + ' no ' + rows.length + ')';
    registerEmpty.hidden = visibleCount !== 0;

    // 2) Kārtošana.
    const sorted = [...rows].sort(cmpRows);
    sorted.forEach(r => register.appendChild(r));

    if (groupMode === 'chrono') return;

    // 3) Grupēšana (tikai redzamās rindas; grupu secība: skaits DESC, tad nosaukums).
    const buckets = new Map();
    sorted.forEach(r => {
      if (r.style.display === 'none') return;
      const key = groupMode === 'person'
        ? (r.dataset.person || '—')
        : (r.dataset.topic || 'Bez tēmas');
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(r);
    });
    const groups = [...buckets.entries()].sort(
      (a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0], 'lv')
    );
    groups.forEach(([name, members]) => {
      const g = document.createElement('div');
      g.className = 'prv2-group';
      const h = document.createElement('h3');
      h.className = 'prv2-group-h';
      h.appendChild(document.createTextNode(name + ' '));
      const n = document.createElement('span');
      n.className = 'prv2-group-n';
      n.textContent = '(' + members.length + ')';
      h.appendChild(n);
      g.appendChild(h);
      members.forEach(m => g.appendChild(m));
      register.appendChild(g);
    });
  }

  function syncSevChips() {
    sevChips.querySelectorAll('.prv2-chip').forEach(ch => {
      const active = ch.dataset.sev === activeSeverity;
      ch.classList.toggle('active', active);
      ch.setAttribute('aria-pressed', String(active));
    });
  }

  sevChips.addEventListener('click', e => {
    const chip = e.target.closest('.prv2-chip');
    if (!chip) return;
    // Single-select ar toggle: aktīvā čipa atkārtots klikšķis = noņemt filtru.
    activeSeverity = (activeSeverity === chip.dataset.sev) ? 'all' : chip.dataset.sev;
    syncSevChips();
    applyFilters();
  });

  function applyFilters() {
    renderRegister();
  }

  // View controls: grouping + sorting
  function setupViewToggle(barId, attr, setter) {
    document.getElementById(barId).addEventListener('click', e => {
      if (!e.target.classList.contains('filter-btn')) return;
      document.querySelectorAll('#' + barId + ' .filter-btn').forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-pressed', 'false');
      });
      e.target.classList.add('active');
      e.target.setAttribute('aria-pressed', 'true');
      setter(e.target.dataset[attr]);
      applyFilters();
    });
  }
  setupViewToggle('group-filter', 'group', v => { groupMode = v; });
  setupViewToggle('sort-filter', 'sort', v => { sortMode = v; });

  // Accordion: izpleš rindas pilno karti (CSS grid-rows animācija)
  register.addEventListener('click', e => {
    const head = e.target.closest('.prv2-row-head');
    if (!head || !register.contains(head)) return;
    const open = head.getAttribute('aria-expanded') !== 'true';
    head.setAttribute('aria-expanded', String(open));
    head.closest('.prv2-row').classList.toggle('open', open);
  });

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

  setupMultiSelect('party-select', 'party-trigger', selectedParties, 'Visas partijas', 'partijas izvēlētas');
  setupMultiSelect('person-select', 'person-trigger', selectedPersons, 'Visas personas', 'personas izvēlētas');

  document.addEventListener('click', e => {
    document.querySelectorAll('.multi-select.open').forEach(s => {
      if (!s.contains(e.target)) s.classList.remove('open');
    });
  });

  // Auto-select person from URL param (?persona=Name)
  const urlParams = new URLSearchParams(location.search);
  const preselect = urlParams.get('persona');
  if (preselect) {
    document.querySelectorAll('#person-select .multi-select-option').forEach(opt => {
      if (opt.dataset.value === preselect) opt.click();
    });
  }

  // Inicializācija: minor_shift rindas noklusēti paslēptas, reģistrs izkārtots.
  applyFilters();

  function resetFilters() {
    activeSeverity = 'all';
    syncSevChips();
    selectedParties.clear();
    selectedPersons.clear();
    document.querySelectorAll('.multi-select-option.selected').forEach(o => o.classList.remove('selected'));
    document.querySelectorAll('.multi-select-trigger.has-selection').forEach(t => {
      t.classList.remove('has-selection');
      const span = t.querySelector('span');
      if (span && t.id === 'party-trigger') span.textContent = 'Visas partijas';
      if (span && t.id === 'person-trigger') span.textContent = 'Visas personas';
    });
  }

  document.getElementById('register-empty-clear').addEventListener('click', () => {
    resetFilters();
    applyFilters();
  });

  function _prv2HashJump() {
    const hash = location.hash;
    if (!hash || !hash.startsWith('#pretruna-')) return;
    let row;
    try { row = document.querySelector(hash); } catch (e) { return; }
    if (!row || !row.classList.contains('prv2-row')) return;

    // Clear all filters so a shared link always surfaces the row.
    resetFilters();
    applyFilters();

    // Izpleš rindas karti un ritina pie tās.
    const head = row.querySelector('.prv2-row-head');
    head.setAttribute('aria-expanded', 'true');
    row.classList.add('open');

    row.scrollIntoView({ behavior: 'smooth', block: 'start' });
    row.classList.add('prv2-card-pulse');
    setTimeout(() => row.classList.remove('prv2-card-pulse'), 2000);
  }
  window.addEventListener('hashchange', _prv2HashJump);
  window.addEventListener('load', _prv2HashJump);
})();
