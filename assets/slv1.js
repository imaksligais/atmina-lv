// slv1.js — saeima.html (15. Saeimas pusloks) klienta puse.
// Stingra CSP: nekāda inline JS; visi teksti jau ir HTML (data-lens-for /
// data-lens-val) — šis fails tikai pārslēdz stāvokli:
//   1) lēca: data-lens uz .slv saknes (krāsas un teksti mainās CSS), URL #lens=…;
//   2) sēdvietas klikšķis: kartīte panelī blakus puslokam (≥768 px) vai
//      apakšējā lapā (šaurā ekrānā); Esc / klikšķis ārpusē aizver, fokuss atpakaļ;
//   3) hover/fokuss: sēdvieta ↔ saraksta rinda izceļ viena otru;
//   4) šaurā ekrānā sarakstu grupas aizvērtas, izņemot pirmo.
// Bez JS: pogas paslēptas, «Saraksta» lēca, sēdvieta = enkurs uz rindu (#dep-…).
(function () {
  var root = document.getElementById('slv');
  if (!root) return;
  var LENSES = ['saraksts', 'v14', 'pozicijas', 'pretrunas'];
  var svg = root.querySelector('.slv-svg');
  var lensBar = root.querySelector('.slv-lenses');
  var pop = document.getElementById('slv-pop');
  var popBody = pop.querySelector('.slv-pop-body');
  var closeBtn = pop.querySelector('.slv-pop-close');
  var backdrop = root.querySelector('.slv-backdrop');
  var wide = window.matchMedia('(min-width: 768px)');
  var seats = {};
  var rows = {};
  root.querySelectorAll('.seat').forEach(function (a) { seats[a.getAttribute('data-slug')] = a; });
  root.querySelectorAll('.slv-dep').forEach(function (d) { rows[d.getAttribute('data-slug')] = d; });
  var activeSeat = null;

  // Lipīgā lēcu josla — zem lipīgās navigācijas, kuras augstums mainās.
  function syncStickyTop() {
    var nav = document.querySelector('.nav');
    if (nav) root.style.setProperty('--slv-sticky-top', nav.offsetHeight + 'px');
  }
  syncStickyTop();
  window.addEventListener('resize', syncStickyTop);

  // ── 1. Lēcas ──
  function setLens(lens, updateUrl) {
    if (LENSES.indexOf(lens) < 0) lens = 'saraksts';
    root.setAttribute('data-lens', lens);
    lensBar.querySelectorAll('.slv-lens').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-lens') === lens ? 'true' : 'false');
    });
    if (updateUrl && window.history && history.replaceState) {
      history.replaceState(null, '', lens === 'saraksts' ? location.pathname + location.search : '#lens=' + lens);
    }
  }
  lensBar.hidden = false;
  lensBar.addEventListener('click', function (e) {
    var b = e.target.closest('.slv-lens');
    if (b) setLens(b.getAttribute('data-lens'), true);
  });

  // ── 2. Kartīte ──
  pop.hidden = false;
  function openCard(slug, seat) {
    var row = rows[slug];
    if (!row) return;
    var card = row.querySelector('.slv-card').cloneNode(true);
    card.querySelectorAll('[id]').forEach(function (n) { n.removeAttribute('id'); });
    popBody.innerHTML = '';
    popBody.appendChild(card);
    pop.style.setProperty('--seat-list', getComputedStyle(row).getPropertyValue('--seat-list'));
    pop.classList.add('has-card');
    if (activeSeat) activeSeat.classList.remove('is-active');
    activeSeat = seat || seats[slug] || null;
    if (activeSeat) activeSeat.classList.add('is-active');
    svg.classList.add('has-active');
    if (!wide.matches) {
      pop.classList.add('is-open');
      pop.setAttribute('role', 'dialog');
      pop.setAttribute('aria-modal', 'true');
      backdrop.hidden = false;
      closeBtn.focus({ preventScroll: true });
    }
  }
  function closeCard(returnFocus) {
    if (!pop.classList.contains('has-card')) return;
    pop.classList.remove('is-open', 'has-card');
    pop.removeAttribute('role');
    pop.removeAttribute('aria-modal');
    backdrop.hidden = true;
    popBody.innerHTML = '';
    svg.classList.remove('has-active');
    var seat = activeSeat;
    if (activeSeat) activeSeat.classList.remove('is-active');
    activeSeat = null;
    if (returnFocus && seat) seat.focus({ preventScroll: true });
  }
  svg.addEventListener('click', function (e) {
    var a = e.target.closest('.seat');
    if (!a) return;
    e.preventDefault();
    var slug = a.getAttribute('data-slug');
    if (activeSeat === a && pop.classList.contains('has-card')) { closeCard(true); return; }
    openCard(slug, a);
  });
  closeBtn.addEventListener('click', function () { closeCard(true); });
  backdrop.addEventListener('click', function () { closeCard(true); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeCard(true);
  });
  document.addEventListener('click', function (e) {
    if (!pop.classList.contains('has-card')) return;
    if (e.target.closest('.slv-pop') || e.target.closest('.seat') || e.target.closest('.slv-lenses')) return;
    closeCard(false);
  });
  wide.addEventListener('change', function () { closeCard(false); });

  // ── 3. Savstarpēja izcelšana ──
  function hot(slug, on) {
    var s = seats[slug];
    var r = rows[slug];
    if (s) s.classList.toggle('is-hot', on);
    if (r) r.classList.toggle('is-hot', on);
  }
  function bindHot(el) {
    var slug = el.getAttribute('data-slug');
    el.addEventListener('mouseenter', function () { hot(slug, true); });
    el.addEventListener('mouseleave', function () { hot(slug, false); });
    el.addEventListener('focusin', function () { hot(slug, true); });
    el.addEventListener('focusout', function () { hot(slug, false); });
  }
  Object.keys(seats).forEach(function (k) { bindHot(seats[k]); });
  Object.keys(rows).forEach(function (k) { bindHot(rows[k]); });

  // ── 4. Grupas šaurā ekrānā + sākuma URL ──
  function openRowFromHash() {
    var h = location.hash.replace(/^#/, '');
    if (h.indexOf('dep-') !== 0) return false;
    var row = document.getElementById(h);
    if (!row) return false;
    var group = row.closest('.slv-group');
    if (group) group.open = true;
    row.open = true;
    row.scrollIntoView({ block: 'center' });
    return true;
  }
  if (!wide.matches) {
    root.querySelectorAll('.slv-group').forEach(function (g, i) { if (i > 0) g.open = false; });
  }
  var m = /^#lens=([a-z0-9]+)$/.exec(location.hash);
  if (m) setLens(m[1], false);
  openRowFromHash();
  window.addEventListener('hashchange', openRowFromHash);
})();
