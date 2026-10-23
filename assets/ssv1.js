// ssv1.js — saites lapas noklusējuma skata skripts (2026-10-18).
//   1) vecās filtru saites (?type|party|person) → spriedzes.html ar to pašu vaicājumu
//      (tabula no saites lapas izņemta; spriedzes.html lasa tos pašus parametrus);
//   2) politiķa meklētājs (datalist) → politiki/<slug>.html#saites;
//   3) poga «Rādīt visu tīklu» ielādē d3 + sav1.js + data/saites-graph.json
//      tikai pēc klikšķa un izsauc window.atminaSaitesGraph.open(data).
// Bez JS lapa strādā: partiju saraksts ir parasts <details> HTML.
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
      search.addEventListener('keydown', function (e) { if (e.key === 'Enter') go(); });
    }

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
          if (status) status.textContent = 'Neizdevās ielādēt tīklu. Mēģiniet vēlreiz.';
        });
    });
  });
})();
