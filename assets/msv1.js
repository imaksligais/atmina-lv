// msv1.js — viens kopīgs filtru nolaižamais saraksts (multi-select) visām lapām.
//
// Agrāk katra lapa (blv1, prv1, sav1, spv1, x-v1, znv1) nesa savu
// setupMultiSelect kopiju. Šeit ir vienīgā: atvēršana (citus tās pašas saimes
// sarakstus aizver), atlase/noņemšana, notīrīšana, etiķete (visi / līdz N
// vērtībām / "N <daudzskaitlis>") un viens kopīgs klikšķis-ārpusē klausītājs.
// Ko darīt pēc izmaiņas (filtrēt sarakstu, sinhronizēt URL), lemj lapa pati
// caur onChange.
//
// Klases .open / .selected / has-selection paliek kā bija — ms-a11y.js tās
// vēro ar MutationObserver un sinhronizē ARIA. Saimes atbilst ms-a11y CONFIGS.
//
// Lietojums (ielādē SINHRONI pirms lapas skripta):
//   var api = window.atminaMultiSelect({
//     root: 'party-select',          // saknes elementa id
//     family: 'multi-select',        // vai 'xv1-select'
//     selected: mySet,               // Set, ko lapa lasa filtrēšanā
//     allLabel: 'Visas partijas',
//     pluralLabel: 'partijas izvēlētas',
//     onChange: applyFilters,        // pēc etiķetes atjaunošanas
//     maxNamed: 2,                   // cik vērtības rādīt etiķetē pa vārdam
//     display: function (v) { return v; },  // vērtība → etiķetes teksts
//   });
//   api.updateLabel(); api.setSelection(['A', 'B']); api.options; api.root
// Atgriež null, ja saknes nav lapā.
(function () {
  "use strict";

  var FAMILIES = {
    "multi-select": {
      root: ".multi-select",
      trigger: ".multi-select-trigger",
      label: "span",               // pirmais <span> trigerī
      option: ".multi-select-option",
      clear: ".multi-select-clear",
      search: ".multi-select-search",
      selectionOnRoot: false,      // has-selection uz trigera
      focusSearch: true,
    },
    "xv1-select": {
      root: ".xv1-select",
      trigger: ".xv1-select-trigger",
      label: ".xv1-select-label",
      option: ".xv1-select-option",
      clear: ".xv1-select-clear",
      search: ".xv1-select-search",
      selectionOnRoot: true,       // has-selection uz saknes (style.css)
      focusSearch: false,          // x lapa meklēšanu atverot nefokusēja
    },
  };

  // Viens klikšķis-ārpusē klausītājs visām saimēm; reģistrē pirmais izsaukums.
  var outsideBound = false;
  function bindOutsideClick() {
    if (outsideBound) return;
    outsideBound = true;
    var roots = Object.keys(FAMILIES).map(function (k) { return FAMILIES[k].root + ".open"; }).join(",");
    document.addEventListener("click", function (e) {
      document.querySelectorAll(roots).forEach(function (s) {
        if (!s.contains(e.target)) s.classList.remove("open");
      });
    });
  }

  window.atminaMultiSelect = function (opts) {
    var fam = FAMILIES[opts.family || "multi-select"];
    var root = document.getElementById(opts.root);
    if (!root) return null;
    var trigger = root.querySelector(fam.trigger);
    var label = trigger.querySelector(fam.label);
    var options = root.querySelectorAll(fam.option);
    var clear = root.querySelector(fam.clear);
    var selected = opts.selected;
    var maxNamed = opts.maxNamed || 2;
    var display = opts.display || function (v) { return v; };
    var onChange = opts.onChange || function () {};
    var selectionEl = fam.selectionOnRoot ? root : trigger;

    bindOutsideClick();

    trigger.addEventListener("click", function (e) {
      e.stopPropagation();
      document.querySelectorAll(fam.root + ".open").forEach(function (s) {
        if (s !== root) s.classList.remove("open");
      });
      root.classList.toggle("open");
      if (!fam.focusSearch) return;
      var search = root.querySelector(fam.search);
      if (search && root.classList.contains("open")) setTimeout(function () { search.focus(); }, 50);
    });

    // Katrai opcijai savs klausītājs (ne deleģēts): ms-a11y Enter/Space un lapu
    // ?persona= priekšatlase sauc opt.click(), un stopPropagation te ir apzināts.
    options.forEach(function (opt) {
      opt.addEventListener("click", function (e) {
        e.stopPropagation();
        var v = opt.dataset.value;
        if (selected.has(v)) { selected.delete(v); opt.classList.remove("selected"); }
        else { selected.add(v); opt.classList.add("selected"); }
        updateLabel();
        onChange();
      });
    });

    if (clear) clear.addEventListener("click", function (e) {
      e.stopPropagation();
      selected.clear();
      options.forEach(function (o) { o.classList.remove("selected"); });
      updateLabel();
      onChange();
    });

    function updateLabel() {
      if (selected.size === 0) {
        label.textContent = opts.allLabel;
        selectionEl.classList.remove("has-selection");
      } else if (selected.size <= maxNamed) {
        label.textContent = Array.from(selected).map(display).join(", ");
        selectionEl.classList.add("has-selection");
      } else {
        label.textContent = selected.size + " " + opts.pluralLabel;
        selectionEl.classList.add("has-selection");
      }
    }

    // Programmatiska izvēle (ķēdes saite, URL parametri) — DOM paliek sinhrons.
    // onChange NEsauc: izsaucējs pats lemj, kad filtrēt.
    function setSelection(values) {
      selected.clear();
      (values || []).forEach(function (v) { selected.add(v); });
      options.forEach(function (o) { o.classList.toggle("selected", selected.has(o.dataset.value)); });
      updateLabel();
    }

    return { root: root, options: options, updateLabel: updateLabel, setSelection: setSelection };
  };
})();
