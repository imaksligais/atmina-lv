// fnv1.js — finanšu lapas tabulu filtrs (CSP-drošs, bez inline JS).
// Aizvieto agrāko inline filterTable(inputId, tableId) funkciju.
// Katram meklēšanas laukam ir data-filter-table="<tabulas-id>" atribūts,
// kas norāda filtrējamās tabulas id (agrākais 2. arguments).
// Deleģēts 'input' klausītājs uz dokumenta — strādā visām 3–4 tabulām vienā vietā.
(function () {
  // Garumzīmju locīšana — kopīgā window.atminaFold (assets/sgv1.js, defer, pirms
  // šī faila); abas puses locītas.
  function fold(s) { return window.atminaFold ? window.atminaFold(s) : String(s).toLowerCase(); }

  document.addEventListener('input', function (e) {
    var input = e.target.closest('input[data-filter-table]');
    if (!input) return;
    var tableId = input.getAttribute('data-filter-table');
    if (!tableId) return;
    var q = fold(input.value);
    var rows = document.querySelectorAll('#' + tableId + ' tbody tr');
    rows.forEach(function (row) {
      var text = fold(row.textContent);
      row.style.display = (!q || text.indexOf(q) !== -1) ? '' : 'none';
    });
  });
})();
