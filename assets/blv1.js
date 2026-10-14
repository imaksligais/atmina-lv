// blv1.js — balsojumu lapas inicializācija (izcelts no templates/balsojumi.html.j2
// inline skripta stingrās CSP dēļ). Ielādēts SINHRONI (bez defer) uzreiz PĒC
// assets/bmv1.js, tāpēc window.balsojumiArchiveRender / window.initBalsojumiMatrica
// jau eksistē, kad šis IIFE izpildās (identiska izpildes secība kā agrāk).
//
// Deleģācija (aizstāj noņemtos onclick/oninput atribūtus):
//   • .subtab-bar .subtab-btn[data-tab]        → window.switchTab
//     (tastatūra: assets/tabs-v1.js, ielādēts pirms šī faila)
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
  // Cilņu klase + ARIA + roving tabindex un bultas/Home/End — assets/tabs-v1.js.
  // activate sauc window.switchTab izsaukuma brīdī → ietīto versiju (matrica).
  var subtabBar = document.querySelector('.subtab-bar');
  var subtabs = window.atminaTabs({
    bar: subtabBar,
    tab: '.subtab-btn[data-tab]',
    activate: function(btn) { window.switchTab(btn.dataset.tab); },
  });

  window.switchTab = function(tab) {
    var listTab = document.getElementById('votes-list-tab');
    var matrixTab = document.getElementById('votes-matrix-tab');
    var billsTab = document.getElementById('bills-list-tab');
    if (subtabs) subtabs.select(subtabBar.querySelector('.subtab-btn[data-tab="' + tab + '"]'));
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
  var selectedMonths = new Set();
  var splitOnly = false;
  var voteSearchQuery = '';

  // ── Vote-list filtering ────────────────────────────────────────────
  // Single rendering path: assets/bmv1.js::balsojumiArchiveRender is the ONLY
  // card renderer. With no filter it loads the recent shard (~1-year window,
  // 105 KB br) and shows its newest 200; escalating "Rādīt vairāk" past that
  // fetches the full archive (303 KB br) once and continues paginating over the
  // whole history. Any active filter goes straight to the full archive so older
  // sessions/topics/deputies are always searchable.
  // Plan: docs/superpowers/plans/archive/2026-06-03-balsojumi-archive-filter.md
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
      months: Array.from(selectedMonths),
      splitOnly: splitOnly,
      q: voteSearchQuery,
    };
  }

  function hasActiveFilter() {
    return !!(selectedTopics.size || selectedDeputies.size || selectedSessions.size ||
              selectedMonths.size || splitOnly || voteSearchQuery);
  }

  function renderArchive(reset) {
    if (!window.balsojumiArchiveRender) return;
    var info = elById('votes-archive-info');
    var cardsDiv = elById('votes-archive-cards');
    var moreBtn = elById('votes-archive-more');
    var hasFilter = hasActiveFilter();
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

  // Atslēgvārdu meklēšana balsojumos (motīvs + kopsavilkums + dok. nr.) —
  // debounce, lai nefiltrētu uz katru taustiņu; jebkurš vaicājums eskalē uz
  // pilno arhīvu (hasFilter ceļš), tāpēc meklē VISĀ vēsturē, ne tikai gadā.
  var voteSearch = elById('vote-search');
  if (voteSearch) {
    var _searchTimer = null;
    voteSearch.addEventListener('input', function() {
      clearTimeout(_searchTimer);
      _searchTimer = setTimeout(function() {
        var q = voteSearch.value.trim();
        if (q === voteSearchQuery) return;
        voteSearchQuery = q;
        applyFilters();
      }, 250);
    });
  }

  function applyFilters() {
    renderArchive(true);
  }

  // Etiķetē rāda opcijas tekstu, ne data-value (sēdēm/mēnešiem tie atšķiras).
  function optionLabels(selectId) {
    var map = {};
    var sel = document.getElementById(selectId);
    if (sel) sel.querySelectorAll('.multi-select-option').forEach(function(opt) {
      var textSpan = opt.querySelector('span:not(.checkbox)');
      map[opt.dataset.value] = textSpan ? textSpan.textContent.trim() : opt.dataset.value;
    });
    return function(v) { return map[v] || v; };
  }

  // Rokturi (setSelection/updateLabel) vajag ārējiem izsaucējiem — mēneša
  // sašaurināšanai, ķēdes saitei, matricas "skatīt sarakstā" — lai izvēli
  // mainītu PROGRAMMATISKI un DOM paliktu sinhrons.
  function voteSelect(root, selected, allLabel, pluralLabel, onChange) {
    return atminaMultiSelect({ root: root, selected: selected, allLabel: allLabel,
      pluralLabel: pluralLabel, display: optionLabels(root), onChange: onChange || applyFilters });
  }

  var topicApi = voteSelect('topic-select', selectedTopics, 'Visas tēmas', 'tēmas izvēlētas');
  var deputyApi = voteSelect('deputy-select', selectedDeputies, 'Visi deputāti', 'deputāti izvēlēti');
  var sessionApi = voteSelect('session-select', selectedSessions, 'Visas sēdes', 'sēdes izvēlētas');
  var monthApi = voteSelect('month-select', selectedMonths, 'Visi mēneši', 'mēneši izvēlēti',
    function() {
      // Pirms pārfiltrēšanas: izmet sēdes ārpus tvēruma un pārzīmē sarakstu.
      dropSessionsOutsideMonths();
      applySessionOptionVisibility();
      applyFilters();
    });

  // ── Divsoļu sesiju filtrs (mēnesis → sēde) ────────────────────────
  // ~340 sēžu datumi vienā nolaižamajā sarakstā bija lietojamības defekts.
  // Mēneša izvēle sašaurina sēžu sarakstu; mēnesis filtrē balsojumus arī pats
  // par sevi, ja neviena konkrēta sēde nav izvēlēta.
  function applySessionOptionVisibility() {
    var sel = document.getElementById('session-select');
    if (!sel) return;
    var search = sel.querySelector('.multi-select-search');
    var q = ((search && search.value) || '').toLowerCase();
    sel.querySelectorAll('.multi-select-option').forEach(function(opt) {
      var inMonth = !selectedMonths.size || selectedMonths.has(opt.dataset.month);
      var inText = !q || opt.textContent.toLowerCase().indexOf(q) !== -1;
      opt.style.display = (inMonth && inText) ? '' : 'none';
    });
  }

  // Mēneša maiņa var izmest jau izvēlētu sēdi ārpus tvēruma. Tādu izvēli
  // NOŅEMAM, nevis atstājam neredzamu — citādi saraksts būtu tukšs, un iemesls
  // paliktu paslēpts aiz aizvērta nolaižamā saraksta.
  function dropSessionsOutsideMonths() {
    if (!selectedMonths.size || !selectedSessions.size) return false;
    var kept = [];
    var dropped = false;
    selectedSessions.forEach(function(d) {
      if (selectedMonths.has(String(d).substring(0, 7))) kept.push(d);
      else dropped = true;
    });
    if (dropped) sessionApi.setSelection(kept);
    return dropped;
  }

  // Meklēšana sēžu sarakstā: ms-a11y.js deleģētais 'input' klausītājs ir
  // reģistrēts PIRMS šī (bmv1/ms-a11y ielādēti agrāk), tāpēc te redzam jau
  // nofiltrēto stāvokli un uzliekam virsū mēneša tvērumu.
  document.addEventListener('input', function(e) {
    if (!e.target.closest) return;
    if (e.target.closest('#session-select')) applySessionOptionVisibility();
    if (e.target.closest('#deputy-select')) hideEmptyDeputyGroups();
  });

  // Frakciju grupu virsraksti nav .multi-select-option, tāpēc meklēšanas
  // filtrs tos neaiztiek — bez šī paliktu virsraksti bez neviena vārda zem tiem.
  function hideEmptyDeputyGroups() {
    document.querySelectorAll('#deputy-select .multi-select-group').forEach(function(g) {
      var any = false;
      var n = g.nextElementSibling;
      while (n && !n.classList.contains('multi-select-group')) {
        if (n.classList.contains('multi-select-option') && n.style.display !== 'none') { any = true; break; }
        n = n.nextElementSibling;
      }
      g.style.display = any ? '' : 'none';
    });
  }

  // ── "Tikai dalītie" ───────────────────────────────────────────────
  // Matricā tāds filtrs bija, sarakstā nebija. Dalīts = vismaz vienā frakcijā
  // ar 3+ balsīm vairākums < 80% (bmv1.js::factionIsSplit — VIENA definīcija,
  // kopīga ar kartītes `is-split` čipu).
  var splitToggle = elById('vote-split-toggle');
  if (splitToggle) {
    splitToggle.addEventListener('click', function() {
      splitOnly = !splitOnly;
      splitToggle.classList.toggle('active', splitOnly);
      splitToggle.setAttribute('aria-pressed', splitOnly ? 'true' : 'false');
      applyFilters();
    });
  }

  // ── T14 ķēdes saite ───────────────────────────────────────────────
  // Kartītes "visi šī dokumenta balsojumi →" meklē pēc dokumenta numura.
  // VISUS pārējos filtrus notīra: saite sola visu ķēdi, tāpēc palicis mēneša
  // vai deputāta filtrs padarītu solījumu nepatiesu.
  function clearAllVoteFilters() {
    topicApi.setSelection([]);
    deputyApi.setSelection([]);
    sessionApi.setSelection([]);
    if (monthApi) monthApi.setSelection([]);
    splitOnly = false;
    if (splitToggle) {
      splitToggle.classList.remove('active');
      splitToggle.setAttribute('aria-pressed', 'false');
    }
    applySessionOptionVisibility();
  }

  elById('votes-archive-cards').addEventListener('click', function(e) {
    var link = e.target.closest && e.target.closest('.vote-chain-link');
    if (!link) return;
    e.preventDefault();
    var docNr = link.dataset.docNr || '';
    clearAllVoteFilters();
    voteSearchQuery = docNr;
    if (voteSearch) voteSearch.value = docNr;
    applyFilters();
    var archive = elById('votes-archive');
    if (archive) archive.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  // Āķis matricas noklusējuma panelim ("Skatīt šīs sēdes balsojumus sarakstā").
  // bmv1.js to izsauc tikai tad, ja tas eksistē, tāpēc matrica strādā arī bez
  // šīs lapas init (tests / atsevišķa iegulšana).
  window.balsojumiSelectSession = function(dateStr) {
    if (!dateStr) return;
    clearAllVoteFilters();
    voteSearchQuery = '';
    if (voteSearch) voteSearch.value = '';
    if (monthApi) monthApi.setSelection([String(dateStr).substring(0, 7)]);
    sessionApi.setSelection([dateStr]);
    applySessionOptionVisibility();
    applyFilters();
    window.switchTab('votes-list');
    var archive = elById('votes-archive');
    if (archive) archive.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

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
      b.classList.toggle('active', b === btn);
      b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
    });
    selectedBillStatus = btn.dataset.status;
    window.applyBillsFilters();
  };

  window.toggleBillType = function(btn) {
    var bt = btn.dataset.billType;
    var on = btn.classList.toggle('active');
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
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

  // Likumprojektu tēmu filtrs — tas pats msv1.js kā pārējiem (agrāk roku
  // rakstīts: etiķete neatjaunojās, citus sarakstus neaizvēra).
  atminaMultiSelect({ root: 'bill-topic-select', selected: selectedBillTopics,
    allLabel: 'Visas tēmas', pluralLabel: 'tēmas izvēlētas',
    onChange: function() { window.applyBillsFilters(); } });

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
