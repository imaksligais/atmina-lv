// blv1.js — balsojumu lapas inicializācija (izcelts no templates/balsojumi.html.j2
// inline skripta stingrās CSP dēļ). Ielādēts SINHRONI (bez defer) uzreiz PĒC
// assets/bmv1.js, tāpēc window.balsojumiArchiveRender / window.initBalsojumiMatrica
// jau eksistē, kad šis IIFE izpildās (identiska izpildes secība kā agrāk).
//
// Deleģācija (aizstāj noņemtos onclick/oninput atribūtus):
//   • .subtab-bar .subtab-btn[data-tab]        → window.switchTab
//   • .bill-status-filter [data-status]        → window.toggleBillStatus
//   • .bill-type-filter [data-bill-type]       → window.toggleBillType
//   • #bill-search (input)                     → window.applyBillsFilters
// window.filterOptions vairs netiek definēts — meklēšanas filtrēšanu pārņem
// assets/ms-a11y.js deleģētais 'input' klausītājs.
(function() {
  // VOTE_TOTAL nāk no #votes-archive data-vote-total atribūta (agrāk Jinja-iegults).
  var archiveEl = document.getElementById('votes-archive');
  var VOTE_TOTAL = archiveEl ? parseInt(archiveEl.getAttribute('data-vote-total'), 10) || 0 : 0;

  // ══════════════════════════════════════
  // Tab switching
  // ══════════════════════════════════════
  window.switchTab = function(tab) {
    var listTab = document.getElementById('votes-list-tab');
    var matrixTab = document.getElementById('votes-matrix-tab');
    var billsTab = document.getElementById('bills-list-tab');
    var btns = document.querySelectorAll('.subtab-btn');
    btns.forEach(function(b) { b.classList.toggle('active', b.dataset.tab === tab); });
    listTab.style.display = (tab === 'votes-list') ? '' : 'none';
    matrixTab.style.display = (tab === 'votes-matrix') ? '' : 'none';
    if (billsTab) billsTab.style.display = (tab === 'bills-list') ? '' : 'none';
  };

  // ══════════════════════════════════════
  // Existing vote list filters
  // ══════════════════════════════════════
  var selectedTopics = new Set();
  var selectedDeputies = new Set();
  var selectedSessions = new Set();

  // ── Vote-list filtering ────────────────────────────────────────────
  // Single rendering path: assets/bmv1.js::balsojumiArchiveRender is the ONLY
  // card renderer. With no filter it loads the recent shard (~1-year window,
  // 105 KB br) and shows its newest 200; escalating "Rādīt vairāk" past that
  // fetches the full archive (303 KB br) once and continues paginating over the
  // whole history. Any active filter goes straight to the full archive so older
  // sessions/topics/deputies are always searchable.
  // Plan: docs/superpowers/plans/2026-06-03-balsojumi-archive-filter.md
  var ARCHIVE = {
    recentSrc: 'data/balsojumi-matrica-recent.json',
    fullSrc: 'data/balsojumi-matrica.json',
    pageSize: 200,
    shown: 0,
    needFull: false,  // sticky: once we escalate to the full archive, stay there
  };

  function elById(id) { return document.getElementById(id); }

  function currentFilters() {
    return {
      topics: Array.from(selectedTopics),
      deputies: Array.from(selectedDeputies),
      sessions: Array.from(selectedSessions),
    };
  }

  function renderArchive(reset) {
    if (!window.balsojumiArchiveRender) return;
    var info = elById('votes-archive-info');
    var cardsDiv = elById('votes-archive-cards');
    var moreBtn = elById('votes-archive-more');
    var hasFilter = selectedTopics.size || selectedDeputies.size || selectedSessions.size;
    if (reset) {
      ARCHIVE.shown = 0;
      cardsDiv.innerHTML = '';
      info.textContent = 'Ielādē balsojumus…';
      moreBtn.style.display = 'none';
      // A fresh filtered query always resolves against the full archive; a
      // cleared filter reverts to the recent shard until escalation.
      ARCHIVE.needFull = !!hasFilter;
    }
    var wantFull = !!hasFilter || ARCHIVE.needFull;
    window.balsojumiArchiveRender(
      ARCHIVE.recentSrc, ARCHIVE.fullSrc, currentFilters(),
      { limit: ARCHIVE.pageSize, offset: ARCHIVE.shown, wantFull: wantFull },
      function(res) {
        cardsDiv.insertAdjacentHTML('beforeend', res.html);
        ARCHIVE.shown = res.shown;
        // Unfiltered recent shard exhausted but more history exists in the full
        // archive → keep the more-button live and flip needFull so the NEXT
        // click re-renders from the full archive. Newest-first ordering makes
        // the recent shard a prefix of full, so ARCHIVE.shown stays valid.
        var moreInShard = res.shown < res.total;
        var moreInArchive = !hasFilter && !ARCHIVE.needFull &&
          res.shown >= res.total && res.total < VOTE_TOTAL;
        if (res.total === 0) {
          info.textContent = 'Nav balsojumu, kas atbilst izvēlētajiem filtriem.';
        } else {
          var shownTotal = (!hasFilter && res.total < VOTE_TOTAL) ? VOTE_TOTAL : res.total;
          info.textContent = 'Rāda ' + res.shown + ' no ' + shownTotal + ' balsojumiem.';
        }
        if (moreInArchive) ARCHIVE.needFull = true;
        moreBtn.style.display = (moreInShard || moreInArchive) ? '' : 'none';
        runVoteHashScroll();
        // Deep-link resolution: if a #vote- hash target is not among the
        // rendered cards, defer to the Matrica tab IMMEDIATELY (old-SSR
        // semantics) — bmv1.js::applyHashScroll resolves it against the full
        // corpus there. Fires at most once (guard), only on the initial
        // page-load render, never on user-driven filter re-renders.
        if (reset && !_voteHashDone && location.hash &&
            location.hash.startsWith('#vote-')) {
          _voteHashDone = true;
          window.switchTab('votes-matrix');
        }
      },
      function(msg) {
        info.textContent = 'Balsojumus neizdevās ielādēt: ' + msg;
      }
    );
  }

  elById('votes-archive-more').addEventListener('click', function() {
    renderArchive(false);
  });

  function applyFilters() {
    renderArchive(true);
  }

  function setupMultiSelect(selectId, triggerId, selectedSet, allLabel, pluralLabel) {
    var select = document.getElementById(selectId);
    var trigger = document.getElementById(triggerId);
    var label = trigger.querySelector('span');
    var valueToLabel = {};
    select.querySelectorAll('.multi-select-option').forEach(function(opt) {
      var textSpan = opt.querySelector('span:not(.checkbox)');
      valueToLabel[opt.dataset.value] = textSpan ? textSpan.textContent.trim() : opt.dataset.value;
    });

    trigger.addEventListener('click', function(e) {
      e.stopPropagation();
      document.querySelectorAll('.multi-select.open').forEach(function(s) {
        if (s.id !== selectId) s.classList.remove('open');
      });
      select.classList.toggle('open');
      var search = select.querySelector('.multi-select-search');
      if (search && select.classList.contains('open')) setTimeout(function() { search.focus(); }, 50);
    });

    select.querySelectorAll('.multi-select-option').forEach(function(opt) {
      opt.addEventListener('click', function(e) {
        e.stopPropagation();
        var val = opt.dataset.value;
        if (selectedSet.has(val)) { selectedSet.delete(val); opt.classList.remove('selected'); }
        else { selectedSet.add(val); opt.classList.add('selected'); }
        updateLabel();
        applyFilters();
      });
    });

    select.querySelector('.multi-select-clear').addEventListener('click', function(e) {
      e.stopPropagation();
      selectedSet.clear();
      select.querySelectorAll('.multi-select-option').forEach(function(o) { o.classList.remove('selected'); });
      updateLabel();
      applyFilters();
    });

    function updateLabel() {
      if (selectedSet.size === 0) { label.textContent = allLabel; trigger.classList.remove('has-selection'); }
      else if (selectedSet.size <= 2) {
        label.textContent = [...selectedSet].map(function(v) { return valueToLabel[v] || v; }).join(', ');
        trigger.classList.add('has-selection');
      }
      else { label.textContent = selectedSet.size + ' ' + pluralLabel; trigger.classList.add('has-selection'); }
    }
  }

  setupMultiSelect('topic-select', 'topic-trigger', selectedTopics, 'Visas tēmas', 'tēmas izvēlētas');
  setupMultiSelect('deputy-select', 'deputy-trigger', selectedDeputies, 'Visi deputāti', 'deputāti izvēlēti');
  setupMultiSelect('session-select', 'session-trigger', selectedSessions, 'Visas sēdes', 'sēdes izvēlētas');

  document.addEventListener('click', function(e) {
    document.querySelectorAll('.multi-select.open').forEach(function(s) {
      if (!s.contains(e.target)) s.classList.remove('open');
    });
  });

  // Highlight vote card if arrived via anchor link. Cards render async (bmv1.js
  // inserts them into #votes-archive-cards), so this runs both here at init AND
  // inside the first renderArchive callback — whichever finds the element first
  // wins; the sticky guard stops it firing twice. If the vote is outside the
  // rendered slice, fall through to the Matrica tab where bmv1.js::applyHashScroll
  // resolves the hash against the full corpus.
  var _voteHashDone = false;
  function runVoteHashScroll() {
    if (_voteHashDone) return;
    if (!location.hash || !location.hash.startsWith('#vote-')) return;
    var target = document.querySelector(location.hash);
    if (target) {
      _voteHashDone = true;
      target.style.outline = '2px solid var(--accent)';
      target.style.outlineOffset = '4px';
      setTimeout(function() { target.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, 100);
    }
  }
  // Best-effort at init (cards not yet inserted, so usually a no-op). The
  // authoritative resolution — scroll-into-view or Matrica-tab fallback — runs
  // in renderArchive's first callback once the cards (and their totals) exist.
  runVoteHashScroll();

  // Single rendering path — populate the archive shell immediately. bmv1.js is
  // loaded synchronously above, so window.balsojumiArchiveRender exists here.
  renderArchive(true);

  // Auto-select deputy from URL param (?deputats=Name)
  var urlParams = new URLSearchParams(location.search);
  var preselect = urlParams.get('deputats');
  if (preselect) {
    document.querySelectorAll('#deputy-select .multi-select-option').forEach(function(opt) {
      if (opt.dataset.value === preselect) opt.click();
    });
  }

  // Switch to matrix tab if ?tab=matrix
  if (urlParams.get('tab') === 'matrix') {
    window.switchTab('votes-matrix');
  }

  // ══════════════════════════════════════
  // Bills list filters
  // ══════════════════════════════════════
  var selectedBillTopics = new Set();
  var selectedBillStatus = '';
  var hiddenBillTypes = new Set();

  window.toggleBillStatus = function(btn) {
    document.querySelectorAll('.bill-status-filter .link-filter-btn').forEach(function(b) {
      b.classList.remove('active');
    });
    btn.classList.add('active');
    selectedBillStatus = btn.dataset.status;
    window.applyBillsFilters();
  };

  window.toggleBillType = function(btn) {
    var bt = btn.dataset.billType;
    btn.classList.toggle('active');
    if (hiddenBillTypes.has(bt)) hiddenBillTypes.delete(bt);
    else hiddenBillTypes.add(bt);
    window.applyBillsFilters();
  };

  window.applyBillsFilters = function() {
    var search = (document.getElementById('bill-search').value || '').toLowerCase();
    var cards = document.querySelectorAll('#bills-grid .bill-card');
    var visible = 0;
    cards.forEach(function(card) {
      var topicOk = selectedBillTopics.size === 0 || selectedBillTopics.has(card.dataset.topic);
      var statusOk = !selectedBillStatus || card.dataset.status === selectedBillStatus;
      var typeOk = !hiddenBillTypes.has(card.dataset.billType);
      var searchOk = !search || (card.dataset.search || '').includes(search);
      var ok = topicOk && statusOk && typeOk && searchOk;
      card.style.display = ok ? '' : 'none';
      if (ok) visible++;
    });
    var empty = document.getElementById('bills-empty-state');
    if (empty) empty.style.display = visible === 0 ? 'block' : 'none';
  };

  // Topic multi-select setup — clone the votes-list pattern but call applyBillsFilters
  if (document.getElementById('bill-topic-select')) {
    var billTopicSelect = document.getElementById('bill-topic-select');
    billTopicSelect.querySelectorAll('.multi-select-option').forEach(function(opt) {
      opt.addEventListener('click', function(e) {
        e.stopPropagation();
        var val = opt.dataset.value;
        if (selectedBillTopics.has(val)) { selectedBillTopics.delete(val); opt.classList.remove('selected'); }
        else { selectedBillTopics.add(val); opt.classList.add('selected'); }
        window.applyBillsFilters();
      });
    });
    var clearBtn = billTopicSelect.querySelector('.multi-select-clear');
    if (clearBtn) clearBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      selectedBillTopics.clear();
      billTopicSelect.querySelectorAll('.multi-select-option').forEach(function(o) { o.classList.remove('selected'); });
      window.applyBillsFilters();
    });
    var trigger = document.getElementById('bill-topic-trigger');
    if (trigger) trigger.addEventListener('click', function(e) {
      e.stopPropagation();
      billTopicSelect.classList.toggle('open');
    });
  }

  // Switch to bills tab if ?tab=bills
  if (urlParams.get('tab') === 'bills') {
    window.switchTab('bills-list');
  }

  // ══════════════════════════════════════
  // Vote Matrix lazy-init (renderer lives in assets/bmv1.js)
  // ══════════════════════════════════════
  var matrixInited = false;
  function initMatrixOnce() {
    if (matrixInited) return;
    var root = document.getElementById('matrix-root');
    if (!root || !window.initBalsojumiMatrica) return;
    matrixInited = true;
    window.initBalsojumiMatrica(root, 'data/balsojumi-matrica-recent.json', 'data/balsojumi-matrica.json');
  }
  // Wrap switchTab so matrix init fires on first activation.
  var _origSwitchTab = window.switchTab;
  window.switchTab = function(tab) {
    _origSwitchTab(tab);
    if (tab === 'votes-matrix') initMatrixOnce();
  };
  // ?tab=matrix URL param re-routes default load to the matrix tab.
  if (urlParams.get('tab') === 'matrix') {
    initMatrixOnce();
  }

  // ══════════════════════════════════════
  // Deleģēti klikšķu/ievades klausītāji (aizstāj noņemtos onclick/oninput)
  // ══════════════════════════════════════
  // Apakšcilnes: .subtab-btn[data-tab] → switchTab (izmanto ietīto versiju,
  // kas iniciē matricu). Reģistrēts PĒC ietīšanas augšā.
  document.querySelector('.subtab-bar').addEventListener('click', function(e) {
    var btn = e.target.closest('.subtab-btn[data-tab]');
    if (!btn) return;
    window.switchTab(btn.dataset.tab);
  });

  // Likumprojektu statusa filtrs: [data-status] → toggleBillStatus.
  var statusFilter = document.querySelector('.bill-status-filter');
  if (statusFilter) statusFilter.addEventListener('click', function(e) {
    var btn = e.target.closest('[data-status]');
    if (!btn) return;
    window.toggleBillStatus(btn);
  });

  // Likumprojektu tipa filtrs: [data-bill-type] → toggleBillType.
  var typeFilter = document.querySelector('.bill-type-filter');
  if (typeFilter) typeFilter.addEventListener('click', function(e) {
    var btn = e.target.closest('[data-bill-type]');
    if (!btn) return;
    window.toggleBillType(btn);
  });

  // Likumprojektu meklēšana: #bill-search ievade → applyBillsFilters.
  var billSearch = document.getElementById('bill-search');
  if (billSearch) billSearch.addEventListener('input', function() {
    window.applyBillsFilters();
  });
})();
