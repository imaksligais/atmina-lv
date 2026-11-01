// lpv1.js — likumprojektu kataloga filtri (likumprojekti.html). Izcelts no
// blv1.js 2026-10-16, kad likumprojekti pārcēlās no balsojumi.html cilnes.
// Meklēšana bez garumzīmēm — tas pats fold kā bmv1.js::foldText. Teksts
// normalizēts vienreiz ielādē, ievadē — tikai vaicājums.
(function () {
  var selectedTopics = new Set();
  var selectedStatus = '';
  var hiddenTypes = new Set();
  var selectedBucket = '';
  var selectedLaw = '';

  function fold(s) {
    return (s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

  var cards = Array.prototype.slice.call(document.querySelectorAll('#bills-grid .bill-card'));
  cards.forEach(function (c) { c._hay = fold(c.dataset.search); });
  var total = cards.length;

  function apply() {
    var q = fold(document.getElementById('bill-search').value).trim();
    var visible = 0;
    cards.forEach(function (card) {
      var ok = (selectedTopics.size === 0 || selectedTopics.has(card.dataset.topic)) &&
        (!selectedStatus || card.dataset.status === selectedStatus) &&
        !hiddenTypes.has(card.dataset.billType) &&
        (!selectedBucket || card.dataset.bucket === selectedBucket) &&
        (!selectedLaw || card.dataset.law === selectedLaw) &&
        (!q || card._hay.indexOf(q) !== -1);
      card.style.display = ok ? '' : 'none';
      if (ok) visible++;
    });
    document.getElementById('bills-count').textContent = 'Rāda ' + visible + ' no ' + total;
    document.getElementById('bills-empty-state').style.display = visible === 0 ? 'block' : 'none';
  }

  document.querySelector('.bill-status-filter').addEventListener('click', function (e) {
    var btn = e.target.closest('[data-status]');
    if (!btn) return;
    document.querySelectorAll('.bill-status-filter .link-filter-btn').forEach(function (b) {
      b.classList.toggle('active', b === btn);
      b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
    });
    selectedStatus = btn.dataset.status;
    apply();
  });

  document.querySelector('.bill-type-filter').addEventListener('click', function (e) {
    var btn = e.target.closest('[data-bill-type]');
    if (!btn) return;
    var on = btn.classList.toggle('active');
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    if (on) hiddenTypes.delete(btn.dataset.billType); else hiddenTypes.add(btn.dataset.billType);
    apply();
  });

  document.getElementById('bill-search').addEventListener('input', apply);

  // Viena izvēle grupā; otrs klikšķis uz tās pašas pogas izvēli noņem.
  function bindSingle(sel, attr, set) {
    var box = document.querySelector(sel);
    if (!box) return;
    box.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-' + attr + ']');
      if (!btn) return;
      var on = btn.getAttribute('aria-pressed') !== 'true';
      box.querySelectorAll('[data-' + attr + ']').forEach(function (b) {
        var me = b === btn && on;
        b.setAttribute('aria-pressed', me ? 'true' : 'false');
        b.classList.toggle('active', me);
      });
      set(on ? btn.dataset[attr] : '');
      apply();
    });
  }
  bindSingle('.lpv1-stages', 'bucket', function (v) { selectedBucket = v; });
  // Kamēr likums izvēlēts, <details> paliek atvērts — citādi aktīvais filtrs
  // paslēptos. Aizvērt var pēc izvēles noņemšanas (otrs klikšķis).
  var lawsBox = document.querySelector('.lpv1-laws');
  bindSingle('.lpv1-laws', 'law', function (v) {
    selectedLaw = v;
    if (v && lawsBox) lawsBox.open = true;
  });
  if (lawsBox) {
    lawsBox.addEventListener('toggle', function () {
      if (!lawsBox.open && selectedLaw) lawsBox.open = true;
    });
  }

  atminaMultiSelect({ root: 'bill-topic-select', selected: selectedTopics,
    allLabel: 'Visas tēmas', pluralLabel: 'tēmas izvēlētas', onChange: apply });
})();
