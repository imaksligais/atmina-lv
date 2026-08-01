/* stv1.js — Statistikas lapu klienta loģika (CSP-drošs ārējais skripts).
 *
 * Viens fails apkalpo abas statistikas lapas; atzaru izvēlas pēc tā, kurš
 * JSON datu bloks atrodas dokumentā:
 *   #stat-cards  → paneļa (dashboard) mini-grafiki (sparklines)
 *   #stat-detail → detaļu lapas galvenais grafiks + notikumu anotācijas
 * Abas atkarīgas no Chart.js (assets/chart.min.js), kas ielādēts sinhroni
 * PIRMS šī skripta (tāpēc DOMContentLoaded uz init pietiek).
 */
(function () {
  'use strict';

  var cssVar = function (n) {
    return getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  };

  // ── Paneļa (dashboard) mini-grafiki ──────────────────────────────
  var cardsEl = document.getElementById('stat-cards');
  if (cardsEl) {
    var CARDS_DATA = JSON.parse(cardsEl.textContent);
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var sparkInstances = [];

    var makeSpark = function (card) {
      var canvas = document.getElementById('spark-' + card.table_id);
      if (!canvas || !card.sparkline_values.length) return null;
      var ctx = canvas.getContext('2d');
      var DOMAIN_COLORS = {
        economy: cssVar('--domain-economy'), social: cssVar('--domain-social'),
        prices: cssVar('--domain-prices'), state: cssVar('--domain-state'),
      };
      var color = DOMAIN_COLORS[card.domain] || DOMAIN_COLORS.economy;
      var gradient = ctx.createLinearGradient(0, 0, 0, 56);
      gradient.addColorStop(0, color + '33');
      gradient.addColorStop(1, 'transparent');
      return new Chart(ctx, {
        type: 'line',
        data: {
          labels: card.sparkline_labels,
          datasets: [{
            data: card.sparkline_values,
            borderColor: color, backgroundColor: gradient,
            borderWidth: 1.75, fill: true, tension: 0.35,
            pointRadius: 0, pointHoverRadius: 3, pointBackgroundColor: color,
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: {display: false},
            tooltip: {
              enabled: true,
              backgroundColor: cssVar('--tooltip-bg'),
              titleColor: cssVar('--text'), bodyColor: cssVar('--text'),
              borderColor: cssVar('--tooltip-border'), borderWidth: 1,
              cornerRadius: 6, displayColors: false, padding: 8,
            },
          },
          scales: { x: {display: false}, y: {display: false} },
          interaction: {intersect: false, mode: 'index'},
          animation: reduce ? false : {duration: 600, delay: card.index * 60},
        }
      });
    };

    var buildSparks = function () {
      CARDS_DATA.forEach(function (card) {
        var chart = makeSpark(card);
        if (chart) sparkInstances.push(chart);
      });
    };

    document.addEventListener('DOMContentLoaded', buildSparks);
    document.addEventListener('atmina:themechange', function () {
      while (sparkInstances.length) sparkInstances.pop().destroy();
      buildSparks();
    });
  }

  // ── Detaļu lapas grafiks + notikumu anotācijas ───────────────────
  var detailEl = document.getElementById('stat-detail');
  if (detailEl) {
    var payload = JSON.parse(detailEl.textContent);
    var DATA = payload.chart;
    var EVENTS = payload.events;
    var DOMAIN = payload.domain;

    var chartInstance = null;
    var activeCategories = new Set(EVENTS.map(function (e) { return e.category; }));
    var highlightedEventIdx = null;

    var buildAnnotations = function () {
      var CATEGORY_COLORS = {
        crisis: '#C62828', policy: cssVar('--yellow'),
        elections: cssVar('--accent'), milestone: cssVar('--green'), government: cssVar('--orange'),
      };
      var pointBorder = cssVar('--bg');
      var annotations = {};
      var labelToIdx = new Map();
      DATA.labels.forEach(function (l, i) { labelToIdx.set(l, i); });
      EVENTS.forEach(function (evt, i) {
        if (!activeCategories.has(evt.category)) return;
        var idx = labelToIdx.get(evt.label);
        if (idx === undefined) return;
        var yVal = DATA.values[idx];
        if (yVal === null || yVal === undefined) return;
        var isHighlighted = highlightedEventIdx === i;
        var isDimmed = highlightedEventIdx !== null && !isHighlighted;
        annotations['line' + i] = {
          type: 'line', xMin: evt.label, xMax: evt.label,
          borderColor: CATEGORY_COLORS[evt.category] + (isHighlighted ? 'C0' : (isDimmed ? '15' : '40')),
          borderWidth: isHighlighted ? 1.5 : 1, borderDash: [3, 3],
        };
        annotations['pt' + i] = {
          type: 'point', xValue: evt.label, yValue: yVal,
          radius: isHighlighted ? 8 : 5,
          backgroundColor: CATEGORY_COLORS[evt.category] + (isDimmed ? '40' : ''),
          borderColor: pointBorder, borderWidth: 2,
        };
      });
      return annotations;
    };

    var eventsAtLabel = function (label) {
      return EVENTS.filter(function (e) {
        return e.label === label && activeCategories.has(e.category);
      });
    };

    var render = function () {
      var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      var DOMAIN_COLORS = {
        economy: cssVar('--domain-economy'), social: cssVar('--domain-social'),
        prices: cssVar('--domain-prices'), state: cssVar('--domain-state'),
      };
      var color = DOMAIN_COLORS[DOMAIN] || DOMAIN_COLORS.economy;
      var ctx = document.getElementById('main-chart').getContext('2d');
      var gradient = ctx.createLinearGradient(0, 0, 0, 440);
      gradient.addColorStop(0, color + '2E');
      gradient.addColorStop(1, 'transparent');
      if (chartInstance) chartInstance.destroy();
      chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
          labels: DATA.labels,
          datasets: [{
            label: DATA.label, data: DATA.values,
            borderColor: color, backgroundColor: gradient,
            borderWidth: 2, fill: true, tension: 0.25,
            pointRadius: DATA.values.length > 60 ? 0 : 2.5,
            pointHoverRadius: 5, pointBackgroundColor: color,
            pointBorderColor: cssVar('--bg'), pointBorderWidth: 1,
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: {display: false},
            annotation: {annotations: buildAnnotations()},
            tooltip: {
              backgroundColor: cssVar('--tooltip-bg'),
              titleColor: cssVar('--text'), bodyColor: cssVar('--text'),
              footerColor: cssVar('--text-soft'),
              borderColor: cssVar('--tooltip-border'), borderWidth: 1,
              cornerRadius: 6, padding: 12, displayColors: false,
              titleFont: {weight: '600', size: 12},
              bodyFont: {size: 13},
              footerFont: {size: 11, weight: '400', style: 'italic'},
              footerMarginTop: 8,
              callbacks: {
                footer: function (items) {
                  if (!items.length) return '';
                  var matching = eventsAtLabel(items[0].label);
                  if (!matching.length) return '';
                  return matching.map(function (e) { return '● ' + e.text; });
                },
              },
            },
          },
          scales: {
            x: {
              ticks: {color: cssVar('--text-muted'), maxTicksLimit: 12, font: {size: 11}},
              grid: {color: cssVar('--chart-grid'), drawTicks: false},
              border: {color: cssVar('--chart-axis')},
            },
            y: {
              ticks: {color: cssVar('--text-muted'), font: {size: 11}},
              grid: {color: cssVar('--chart-grid'), drawTicks: false},
              border: {display: false},
            },
          },
          interaction: {intersect: false, mode: 'index'},
          animation: reduce ? false : {duration: 800},
        }
      });
    };

    var toggleCategory = function (cat) {
      if (activeCategories.has(cat)) activeCategories.delete(cat);
      else activeCategories.add(cat);
      document.querySelectorAll('.stat-event-chip').forEach(function (chip) {
        chip.classList.toggle('active', activeCategories.has(chip.dataset.cat));
      });
      document.querySelectorAll('.stat-event-legend-item').forEach(function (item) {
        item.classList.toggle('hidden', !activeCategories.has(item.dataset.cat));
      });
      if (chartInstance) {
        chartInstance.options.plugins.annotation.annotations = buildAnnotations();
        chartInstance.update('none');
      }
    };

    var setHighlight = function (idx) {
      if (highlightedEventIdx === idx) return;
      highlightedEventIdx = idx;
      if (!chartInstance) return;
      chartInstance.options.plugins.annotation.annotations = buildAnnotations();
      chartInstance.update('none');
    };

    document.addEventListener('DOMContentLoaded', function () {
      document.querySelectorAll('.stat-event-chip').forEach(function (chip) {
        chip.addEventListener('click', function () { toggleCategory(chip.dataset.cat); });
      });
      document.querySelectorAll('.stat-event-legend-item').forEach(function (item) {
        var idx = parseInt(item.dataset.evtIdx, 10);
        item.addEventListener('mouseenter', function () { item.classList.add('hovered'); setHighlight(idx); });
        item.addEventListener('mouseleave', function () { item.classList.remove('hovered'); setHighlight(null); });
      });
      render();
    });
    document.addEventListener('atmina:themechange', render);
  }
})();
