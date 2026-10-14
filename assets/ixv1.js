// ixv1.js — sākumlapas (index) klienta puses skripts:
//   1) tendenču stabiņu diagrammas (Chart.js) ar klikšķa caureju uz tēmām/politiķiem,
//   2) vēlēšanu atskaite pēc lasītāja vietējā datuma,
//   3) hero sekcijas karuselis (kartītes + punkti).
//
// Tendenču dati nāk no <script type="application/json" id="trends-data"> bloka
// (emitēts tikai tad, kad trends_data ir pieejams). Ja bloka nav — kārtīgi
// pārtraucam (no-op), diagrammas neveidojas. Karuselis darbojas vienmēr.
// Chart globālais mainīgais tiek definēts ar chart.min.js (defer), kas ielādēts
// PIRMS šī faila; defer saglabā secību, tāpēc Chart ir pieejams šeit.

// --- 1. Tendenču diagrammas ---
window.addEventListener('DOMContentLoaded', function() {
  var trendsEl = document.getElementById('trends-data');
  if (!trendsEl) return;
  var td = JSON.parse(trendsEl.textContent);
  var cssVar = function(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); };
  var topicLabels = td.topics.labels.slice(0, 10);
  var polLabels = td.politicians.labels.slice(0, 10);
  var polSlugs = td.politicians.slugs.slice(0, 10);
  var topicColors = td.topics.colors.slice(0, 10).map(muteForPaper);
  var polColors = td.politicians.colors.slice(0, 10).map(muteForPaper);
  var topicsChart, politiciansChart;
  var mqCompact = window.matchMedia('(max-width: 480px)');

  /* Kanoniskā tēmu/partiju palete ir paredzēta čipiem un ikonām — uz krēma
     fona tīrā formā tā izskatās sveša. Stabiņiem saglabājam katras krāsas
     nokrāsu (hue), bet ierobežojam piesātinājumu un gaišumu, lai harmonētu
     ar lapas redakcionālo toni. */
  function muteForPaper(hex) {
    var m = /^#?([0-9a-f]{6})$/i.exec(hex || '');
    if (!m) return hex;
    var r = parseInt(m[1].slice(0, 2), 16) / 255,
        g = parseInt(m[1].slice(2, 4), 16) / 255,
        b = parseInt(m[1].slice(4, 6), 16) / 255;
    var max = Math.max(r, g, b), min = Math.min(r, g, b);
    var h = 0, s = 0, l = (max + min) / 2;
    if (max !== min) {
      var d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
      else if (max === g) h = (b - r) / d + 2;
      else h = (r - g) / d + 4;
      h /= 6;
    }
    s = Math.min(s, 0.42);
    l = Math.min(Math.max(l, 0.42), 0.56);
    var q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    var p = 2 * l - q;
    var hue2rgb = function(t) {
      if (t < 0) t += 1; if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    };
    var to2 = function(v) { return ('0' + Math.round(v * 255).toString(16)).slice(-2); };
    return '#' + to2(hue2rgb(h + 1/3)) + to2(hue2rgb(h)) + to2(hue2rgb(h - 1/3));
  }

  function buildTrends() {
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    /* ≤480 px: augstāks kanvas (aspectRatio 0.9 → 10 stabiņi pa ~24–29 px
       pieskāriena mērķim), lai stabiņi netiktu saspiesti ~150 px, un
       autoSkip: false, jo Chart.js citādi rāda tikai katru otro etiķeti. */
    var compact = mqCompact.matches;
    Chart.defaults.color = cssVar('--text-muted');
    Chart.defaults.borderColor = cssVar('--border');
    Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

    topicsChart = new Chart(document.getElementById('topicsChart'), {
      type: 'bar',
      data: {
        labels: topicLabels,
        datasets: [{
          data: td.topics.values.slice(0, 10), backgroundColor: topicColors, borderRadius: 4,
          /* compact: biezāki stabiņi (≈24 px) — pieklājīgs pieskāriena mērķis. */
          categoryPercentage: compact ? 1.0 : 0.8
        }]
      },
      options: {
        animation: reduce ? false : undefined,
        indexAxis: 'y',
        aspectRatio: compact ? 0.9 : 2,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: cssVar('--border') } },
          y: { grid: { display: false }, ticks: { autoSkip: !compact } }
        },
        onClick: function(e, elements) {
          if (elements.length > 0) {
            var topic = topicLabels[elements[0].index];
            window.location.href = 'pozicijas.html?tema=' + encodeURIComponent(topic);
          }
        },
        onHover: function(e, elements) {
          e.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
        }
      }
    });

    politiciansChart = new Chart(document.getElementById('politiciansChart'), {
      type: 'bar',
      data: {
        labels: polLabels,
        datasets: [{
          data: td.politicians.values.slice(0, 10), backgroundColor: polColors, borderRadius: 4,
          categoryPercentage: compact ? 1.0 : 0.8
        }]
      },
      options: {
        animation: reduce ? false : undefined,
        indexAxis: 'y',
        aspectRatio: compact ? 0.9 : 2,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: cssVar('--border') } },
          y: { grid: { display: false }, ticks: { autoSkip: !compact } }
        },
        onClick: function(e, elements) {
          if (elements.length > 0) {
            window.location.href = 'politiki/' + polSlugs[elements[0].index] + '.html';
          }
        },
        onHover: function(e, elements) {
          e.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
        }
      }
    });
  }

  function rebuildTrends() {
    if (topicsChart) topicsChart.destroy();
    if (politiciansChart) politiciansChart.destroy();
    buildTrends();
  }

  buildTrends();

  document.addEventListener('atmina:themechange', rebuildTrends);
  /* Robežas 480 px šķērsošana (tālruņa rotācija, logs vilkts šaurāks/platāks)
     maina gan kanvas augstumu, gan autoSkip — pārzīmējam ar tiem pašiem datiem. */
  if (mqCompact.addEventListener) mqCompact.addEventListener('change', rebuildTrends);
});

// --- 2. Vēlēšanu atskaite pēc lasītāja vietējā datuma ---
// Serveris ieraksta dienu skaitu renderēšanas brīdī, bet lapa var palikt
// nemainīta vairākas dienas (deploy nav ik dienu), tāpēc skaitlis novecotu.
// Datumu lasām kā vietējo pusnakti (new Date(y, m-1, d)), NE new Date('Y-M-D'),
// kas ir UTC pusnakts un laika joslās uz rietumiem no UTC nobīdītu dienu.
// Math.round izlīdzina vasaras laika maiņas stundu. Vēlēšanu nosaukums nāk no
// data-* atribūtiem šablonā (templates/index.html.j2).
(function() {
  var el = document.querySelector('.hero-election[data-election]');
  if (!el) return;
  var parts = (el.getAttribute('data-election') || '').split('-');
  if (parts.length !== 3) return;
  var election = new Date(+parts[0], +parts[1] - 1, +parts[2]);
  var now = new Date();
  var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  var d = Math.round((election - today) / 86400000);
  if (isNaN(d)) return;
  var days = el.querySelector('.hero-election-days');
  var label = el.querySelector('.hero-election-label');
  if (!days || !label) return;
  if (d < 0) {
    el.hidden = true;
  } else if (d === 0) {
    el.hidden = false;
    days.textContent = 'Šodien';
    label.textContent = '— ' + el.getAttribute('data-election-today');
  } else {
    el.hidden = false;
    days.textContent = String(d);
    label.textContent = ((d % 10 === 1 && d % 100 !== 11) ? 'diena' : 'dienas') +
      ' ' + el.getAttribute('data-election-to');
  }
})();

// --- 3. Hero karuselis: TIKAI manuāla navigācija ---
// T1 (2026-09-05): kartīte tagad nes pilnu analīzes kopsavilkumu un kontekstu,
// tāpēc automātiska pārslēgšanās atņemtu lasītājam tekstu pusteikumā. Auto-
// advance (`setInterval`) ir apzināti noņemts; līdz ar to atkrita arī `paused`
// (peles pauze) un `reduce` (prefers-reduced-motion vārti) — bez kustības
// tiem nav ko apturēt. Punkti ir <button>, tātad tastatūra strādā bez papildu
// koda. Vienai kartītei šablons punktus nerenderē, un šis zars atgriežas uzreiz.
(function() {
  var feature = document.getElementById('heroFeature');
  if (!feature) return;
  var cards = feature.querySelectorAll('.hero-feature-card');
  var dots = feature.querySelectorAll('.hero-feature-dot');
  if (cards.length <= 1) return;

  var i = 0;
  function show(n) {
    cards[i].classList.remove('is-active');
    if (dots[i]) dots[i].classList.remove('is-active');
    i = (n + cards.length) % cards.length;
    cards[i].classList.add('is-active');
    if (dots[i]) dots[i].classList.add('is-active');
  }
  dots.forEach(function(dot, n) {
    dot.addEventListener('click', function(e) {
      e.preventDefault(); e.stopPropagation();
      show(n);
    });
  });
})();
