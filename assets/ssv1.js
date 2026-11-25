// ssv1.js — saites lapas noklusējuma skata skripts (2026-10-18).
//   1) vecās filtru saites (?type|party|person) → spriedzes.html ar to pašu vaicājumu
//      (tabula no saites lapas izņemta; spriedzes.html lasa tos pašus parametrus);
//   2) politiķa meklētājs (datalist) → politiki/<slug>.html#saites;
//   3) poga «Rādīt visu tīklu» ielādē d3 + sav1.js + data/saites-graph.json
//      tikai pēc klikšķa un izsauc window.atminaSaitesGraph.open(data).
//   4) partiju tabula: rinda atver savus pārus nākamajā rindā, vienlaikus viena
//      partija (2026-11-22). Bez JS lapa strādā: visi pāri redzami.
(function () {
  var params = new URLSearchParams(location.search);
  if (params.has('type') || params.has('party') || params.has('person')) {
    location.replace('spriedzes.html' + location.search);
    return;
  }

  // Tas pats ?v= kā šim failam — kešs atjaunojas kopā ar pārējiem aktīviem.
  var me = document.currentScript;
  var version = me && me.src ? new URL(me.src).search : '';

  document.addEventListener('DOMContentLoaded', function () {
    var search = document.getElementById('saites-search');
    var list = document.getElementById('saites-politicians');
    if (search && list) {
      var go = function () {
        var want = search.value.trim();
        var opts = list.querySelectorAll('option');
        for (var i = 0; i < opts.length; i++) {
          if (opts[i].value === want) {
            location.href = 'politiki/' + opts[i].dataset.slug + '.html#saites';
            return;
          }
        }
      };
      search.addEventListener('change', go);
      search.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.isComposing) go();
      });
    }

    // Partiju tabula: JS pāru rindas paslēpj tikai šeit, tāpēc bez JS tās redz.
    var toggles = document.querySelectorAll('.saites-party-toggle');
    function setOpen(t, open) {
      t.setAttribute('aria-expanded', open ? 'true' : 'false');
      var row = document.getElementById(t.getAttribute('aria-controls'));
      if (row) row.hidden = !open;
    }
    toggles.forEach(function (t) { setOpen(t, false); });
    document.querySelectorAll('.saites-party-row').forEach(function (row) {
      var t = row.querySelector('.saites-party-toggle');
      if (!t) return;
      // Visa rinda ir vadīkla (§0); poga dod tastatūru un ekrāna lasītāju.
      row.addEventListener('click', function () {
        var open = t.getAttribute('aria-expanded') !== 'true';
        toggles.forEach(function (o) { if (o !== t) setOpen(o, false); });
        setOpen(t, open);
      });
    });

    var btn = document.getElementById('saites-open-graph');
    var block = document.getElementById('saites-graph-block');
    var status = document.getElementById('saites-graph-status');
    if (!btn || !block) return;

    function loadScript(src) {
      return new Promise(function (resolve, reject) {
        var s = document.createElement('script');
        s.src = src + version;
        s.onload = resolve;
        s.onerror = function () { reject(new Error(src)); };
        document.head.appendChild(s);
      });
    }

    btn.addEventListener('click', function () {
      btn.disabled = true;
      if (status) status.textContent = 'Ielādē tīklu…';
      // Bloks jāatklāj PIRMS open(): grafs mēra konteinera izmērus.
      block.hidden = false;
      loadScript('assets/d3.v7.min.js')
        .then(function () { return loadScript('assets/sav1.js'); })
        .then(function () { return fetch('data/saites-graph.json'); })
        .then(function (r) { if (!r.ok) throw new Error('saites-graph ' + r.status); return r.json(); })
        .then(function (data) {
          window.atminaSaitesGraph.open(data);
          btn.hidden = true;
          if (status) status.textContent = '';
        })
        .catch(function () {
          block.hidden = true;
          btn.disabled = false;
          if (status) status.textContent = 'Nevar ielādēt tīklu. Pārbaudi internetu un mēģini vēlreiz.';
          btn.textContent = 'Mēģināt vēlreiz';
        });
    });
  });
})();
