/*
 * Analīžu lapas skripts (analizes.html).
 * Source: assets/anv1.js → copied to output/atmina/assets/anv1.js.
 *
 * - Cilņu pārslēgšana (Dienas pārskati / Sintēzes / Tematiskās / Tendences)
 *   ar deleģētu klikšķi uz [data-anal-tab] (nav inline onclick — strikts CSP).
 * - URL-hash dziļsaite (#tematic / #sintezes / #daily / #trends).
 * - Tendenču grafiku slinkā inicializācija — dati nāk no
 *   <script type="application/json" id="trends-data"> bloka; ja bloka nav
 *   (trends_data tukšs), grafiki tiek izlaisti (no-op).
 */
(function () {
  "use strict";

  var _trendsChartsInit = false;

  window.switchAnalTab = function (tab) {
    document.getElementById('anal-tematic').style.display = tab === 'tematic' ? '' : 'none';
    document.getElementById('anal-sintezes').style.display = tab === 'sintezes' ? '' : 'none';
    document.getElementById('anal-daily').style.display = tab === 'daily' ? '' : 'none';
    document.getElementById('anal-trends').style.display = tab === 'trends' ? '' : 'none';
    document.querySelectorAll('.pagehead-tab').forEach(function (b) { b.classList.remove('active'); });
    document.getElementById('tab-' + tab).classList.add('active');
    if (tab === 'trends' && !_trendsChartsInit) {
      _initTrendsCharts();
      _trendsChartsInit = true;
    }
  };

  // Deleģēts klikšķis uz cilnēm — aizstāj inline onclick.
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-anal-tab]');
    if (!btn) return;
    window.switchAnalTab(btn.getAttribute('data-anal-tab'));
  });

  // Open the right tab based on URL hash (#tematic / #sintezes / #daily / #trends)
  (function () {
    var openFromHash = function () {
      var hash = (location.hash || '').replace('#', '');
      if (hash === 'tematic' || hash === 'sintezes' || hash === 'daily' || hash === 'trends') {
        window.switchAnalTab(hash);
      }
    };
    // chart.min.js is deferred — wait for DOM (+ deferred scripts) so a
    // #trends deep-link can build charts with Chart already loaded.
    if (document.readyState === 'loading') {
      window.addEventListener('DOMContentLoaded', openFromHash);
    } else {
      openFromHash();
    }
    window.addEventListener('hashchange', openFromHash);
  })();

  function _initTrendsCharts() {
    var el = document.getElementById('trends-data');
    if (!el) return;
    var trendsData = JSON.parse(el.textContent);
    var cssVar = function (n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); };
    var topicsChart, politiciansChart, timelineChart;

    function buildTrendsCharts() {
      var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      Chart.defaults.color = cssVar('--text-muted');
      Chart.defaults.borderColor = cssVar('--border');
      Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

      topicsChart = new Chart(document.getElementById('topicsChart'), {
        type: 'bar',
        data: {
          labels: trendsData.topics.labels,
          datasets: [{
            data: trendsData.topics.values,
            backgroundColor: cssVar('--blue'),
            borderRadius: 4
          }]
        },
        options: {
          animation: reduce ? false : undefined,
          indexAxis: 'y',
          plugins: { legend: { display: false } },
          scales: { x: { grid: { color: cssVar('--border') } }, y: { grid: { display: false } } }
        }
      });

      politiciansChart = new Chart(document.getElementById('politiciansChart'), {
        type: 'bar',
        data: {
          labels: trendsData.politicians.labels,
          datasets: [{
            data: trendsData.politicians.values,
            backgroundColor: cssVar('--blue'),
            borderRadius: 4
          }]
        },
        options: {
          animation: reduce ? false : undefined,
          indexAxis: 'y',
          plugins: { legend: { display: false } },
          scales: { x: { grid: { color: cssVar('--border') } }, y: { grid: { display: false } } }
        }
      });

      timelineChart = new Chart(document.getElementById('timelineChart'), {
        type: 'line',
        data: {
          labels: trendsData.timeline.labels,
          datasets: [
            {
              label: 'Pozīcijas',
              data: trendsData.timeline.claims,
              borderColor: cssVar('--blue'),
              backgroundColor: cssVar('--blue') + '1A',
              fill: true,
              tension: 0.3
            },
            {
              label: 'Dokumenti',
              data: trendsData.timeline.documents,
              borderColor: cssVar('--green'),
              backgroundColor: cssVar('--green') + '1A',
              fill: true,
              tension: 0.3
            }
          ]
        },
        options: {
          animation: reduce ? false : undefined,
          plugins: { legend: { labels: { usePointStyle: true } } },
          scales: {
            x: { grid: { color: cssVar('--border') } },
            y: { grid: { color: cssVar('--border') }, beginAtZero: true }
          }
        }
      });
    }

    buildTrendsCharts();

    document.addEventListener('atmina:themechange', function () {
      if (topicsChart) topicsChart.destroy();
      if (politiciansChart) politiciansChart.destroy();
      if (timelineChart) timelineChart.destroy();
      buildTrendsCharts();
    });
  }
})();
