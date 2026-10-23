// blv1.js — balsojumu lapas inicializācija (izcelts no templates/balsojumi.html.j2
// inline skripta stingrās CSP dēļ). Ielādēts SINHRONI (bez defer) uzreiz PĒC
// assets/bmv1.js, tāpēc window.balsojumiArchiveRender / window.balsojumiVoteDate
// jau eksistē, kad šis IIFE izpildās (identiska izpildes secība kā agrāk).
//
// Matricas cilne izņemta 2026-10-16 — lapā ir tikai saraksts, bez cilņu joslas.
// window.filterOptions vairs netiek definēts — meklēšanas filtrēšanu pārņem
// assets/ms-a11y.js deleģētais 'input' klausītājs.
(function() {
  // Likumprojekti 2026-10-16 pārcēlās uz savu lapu; vecā cilnes saite ved turp.
  if (new URLSearchParams(location.search).get('tab') === 'bills') {
    location.replace('likumprojekti.html');
    return;
  }
  // Matrica 2026-10-16 izņemta; vecā `?tab=matrix` saite atver sarakstu.
  // Noņem TIKAI `tab` — citi filtri un #vote- enkurs paliek.
  (function dropMatrixTabParam() {
    var p = new URLSearchParams(location.search);
    if (p.get('tab') !== 'matrix' || !window.history || !history.replaceState) return;
    p.delete('tab');
    var qs = p.toString();
    history.replaceState(null, '', location.pathname + (qs ? '?' + qs : '') + location.hash);
  })();

  // VOTE_TOTAL nāk no #votes-archive data-vote-total atribūta (agrāk Jinja-iegults).
  var archiveEl = document.getElementById('votes-archive');
  var VOTE_TOTAL = archiveEl ? parseInt(archiveEl.getAttribute('data-vote-total'), 10) || 0 : 0;

  // ══════════════════════════════════════
  // Vote list filters
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

  // Paaudzes skaitītājs: ja lietotājs maina filtrus, kamēr iepriekšējais
  // renders vēl ielādē JSON, vecā atbilde tiek izmesta — citādi abas
  // pievienotu kartītes. (Datu pazemināšanu pret novēlotu recent atbildi sargā
  // bmv1.js::loadInto, ne šis skaitītājs.)
  var renderGen = 0;

  // opts (tikai #vote- dziļās saites mašīnai):
  //   hashDriven — šo reset renderu izraisīja hash apstrāde; tā paaudze kļūst
  //                par voteHash.gen PIRMS ielādes (ar jau ielādētiem datiem callback
  //                izpildās sinhroni šī izsaukuma iekšienē).
  //   wantFull   — pārraksta «filtrs → pilnais arhīvs»: recent dienas filtrs ir
  //                pilnīgs, jo shards griezts pa veselām dienām.
  function renderArchive(reset, opts) {
    if (!window.balsojumiArchiveRender) return;
    opts = opts || {};
    if (reset) renderGen++;
    var gen = renderGen;
    if (reset && opts.hashDriven) voteHash.gen = gen;
    var info = elById('votes-archive-info');
    var cardsDiv = elById('votes-archive-cards');
    var moreBtn = elById('votes-archive-more');
    var hasFilter = hasActiveFilter();
    if (reset) {
      ARCHIVE.shown = 0;
      seatPopClose();   // kartītes (un aktīvais kvadrātiņš) tūlīt pazudīs
      cardsDiv.innerHTML = '';
      info.textContent = 'Ielādē balsojumus…';
      moreBtn.style.display = 'none';
      // A fresh filtered query always resolves against the full archive; a
      // cleared filter reverts to the recent shard until escalation.
      ARCHIVE.needFull = !!hasFilter;
      if (typeof opts.wantFull === 'boolean') ARCHIVE.needFull = opts.wantFull;
    }
    // Pēc reset needFull jau ietver filtru (vai mašīnas pārrakstījumu), tāpēc
    // lapošana (reset=false) to manto — arī dziļās saites automātiskā lapa.
    var wantFull = ARCHIVE.needFull;
    window.balsojumiArchiveRender(
      ARCHIVE.recentSrc, ARCHIVE.fullSrc, currentFilters(),
      { limit: ARCHIVE.pageSize, offset: ARCHIVE.shown, wantFull: wantFull },
      function(res) {
        if (gen !== renderGen) return;
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
        voteHashStep(reset, gen, res);
      },
      function(msg) {
        if (gen !== renderGen) return;
        info.textContent = 'Balsojumus neizdevās ielādēt: ' + msg;
      }
    );
  }

  // ── #vote-N dziļā saite ───────────────────────────────────────────
  // Viens stāvokļa mainīgais (ne vairāki karogi):
  //   idle      — gaida pirmo renderu ar hash;
  //   resolving — mērķis nav pirmajā renderā; balsojumiVoteDate meklē datumu;
  //   paging    — dienas filtrs uzlikts; renderi ar paaudzi voteHash.gen lapo,
  //               līdz mērķis atrasts vai diena parādīta visa;
  //   done      — atrasts, nav atrasts, kļūda vai atcelts (lietotāja filtrs).
  // Ja mērķis ir jau pirmajā renderā, filtri netiek mainīti.
  var voteHash = {
    state: (location.hash && location.hash.indexOf('#vote-') === 0) ? 'idle' : 'done',
    gen: 0,
  };

  function voteHashStep(reset, gen, res) {
    if (voteHash.state === 'idle') {
      if (!reset) return;
      if (runVoteHashScroll()) return;
      resolveVoteHash(gen);
    } else if (voteHash.state === 'paging' && gen === voteHash.gen) {
      if (runVoteHashScroll()) return;
      if (res.shown < res.total) renderArchive(false);
      else voteHash.state = 'done';
    }
  }

  function resolveVoteHash(gen) {
    // Stāvokli uzliek PIRMS izsaukuma — callback var būt sinhrons.
    voteHash.state = 'resolving';
    var vid = parseInt(location.hash.slice('#vote-'.length), 10);
    var info = elById('votes-archive-info');
    function stale() { return voteHash.state !== 'resolving' || gen !== renderGen; }
    window.balsojumiVoteDate(vid, function(dateStr) {
      if (stale()) return;
      if (!dateStr) {
        voteHash.state = 'done';
        info.textContent = 'Balsojums nav atrasts arhīvā.';
        return;
      }
      selectSessionDay(dateStr);
      // `paging` PIRMS applyFilters: ar ielādētiem datiem dienas renders un
      // tā voteHashStep izpildās sinhroni applyFilters iekšienē.
      voteHash.state = 'paging';
      // Pilnais arhīvs vajadzīgs tikai, ja datums bija tikai tajā — tad
      // balsojumiVoteDate to jau ielādēja; recent diena ir pilnīga.
      applyFilters({ hashDriven: true, wantFull: false });
    }, function(msg) {
      if (stale()) return;
      voteHash.state = 'done';
      info.textContent = 'Balsojumus neizdevās ielādēt: ' + msg;
    });
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
        userApplyFilters();
      }, 250);
    });
  }

  function applyFilters(opts) {
    writeFiltersToUrl();
    renderArchive(true, opts);
  }

  // Lietotāja filtru maiņa (vadīklas, meklēšana, pogas, ķēdes saite) atceļ
  // nepabeigtu #vote- apstrādi — tā vairs nepārslēdz filtrus atpakaļ. Pati
  // applyFilters to nedara: to lieto arī dziļās saites mašīna.
  function userApplyFilters() {
    voteHash.state = 'done';
    applyFilters();
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
  // sašaurināšanai, ķēdes saitei, #vote- dienas atlasei — lai izvēli
  // mainītu PROGRAMMATISKI un DOM paliktu sinhrons.
  function voteSelect(root, selected, allLabel, pluralLabel, onChange) {
    return atminaMultiSelect({ root: root, selected: selected, allLabel: allLabel,
      pluralLabel: pluralLabel, display: optionLabels(root), onChange: onChange || userApplyFilters });
  }

  var topicApi = voteSelect('topic-select', selectedTopics, 'Visas tēmas', 'tēmas izvēlētas');
  var deputyApi = voteSelect('deputy-select', selectedDeputies, 'Visi deputāti', 'deputāti izvēlēti');
  var sessionApi = voteSelect('session-select', selectedSessions, 'Visas sēdes', 'sēdes izvēlētas');
  var monthApi = voteSelect('month-select', selectedMonths, 'Visi mēneši', 'mēneši izvēlēti',
    function() {
      // Pirms pārfiltrēšanas: izmet sēdes ārpus tvēruma un pārzīmē sarakstu.
      dropSessionsOutsideMonths();
      applySessionOptionVisibility();
      userApplyFilters();
    });

  // ── Divsoļu sesiju filtrs (mēnesis → sēde) ────────────────────────
  // ~340 sēžu datumi vienā nolaižamajā sarakstā bija lietojamības defekts.
  // Mēneša izvēle sašaurina sēžu sarakstu; mēnesis filtrē balsojumus arī pats
  // par sevi, ja neviena konkrēta sēde nav izvēlēta.
  function applySessionOptionVisibility() {
    var sel = document.getElementById('session-select');
    if (!sel) return;
    var search = sel.querySelector('.multi-select-search');
    // Tā pati locīšana kā ms-a11y.js meklēšanā (window.atminaFold, sgv1.js).
    var fold = function(s) { return window.atminaFold ? window.atminaFold(s) : String(s).toLowerCase(); };
    var q = fold((search && search.value) || '');
    sel.querySelectorAll('.multi-select-option').forEach(function(opt) {
      var inMonth = !selectedMonths.size || selectedMonths.has(opt.dataset.month);
      var inText = !q || fold(opt.textContent).indexOf(q) !== -1;
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
  // Dalīts = vismaz vienā frakcijā
  // ar 3+ balsīm vairākums < 80% (bmv1.js::factionIsSplit — VIENA definīcija,
  // kopīga ar kartītes `is-split` čipu).
  var splitToggle = elById('vote-split-toggle');
  if (splitToggle) {
    splitToggle.addEventListener('click', function() {
      splitOnly = !splitOnly;
      splitToggle.classList.toggle('active', splitOnly);
      splitToggle.setAttribute('aria-pressed', splitOnly ? 'true' : 'false');
      userApplyFilters();
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
    userApplyFilters();
    var archive = elById('votes-archive');
    if (archive) archive.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  // Izsekoto politiķu tabula tiek uzbūvēta tikai pirmajā <details> atvēršanā
  // (bmv1.js::balsojumiTrackedHtml). `toggle` neburbuļo — tāpēc capture.
  document.addEventListener('toggle', function(e) {
    var d = e.target;
    if (!d || !d.classList || !d.classList.contains('vote-tracked')) return;
    if (!d.open || d.dataset.filled) return;
    var html = window.balsojumiTrackedHtml(d.dataset.vid);
    if (!html) return;
    d.dataset.filled = '1';
    d.insertAdjacentHTML('beforeend', html);
  }, true);

  // ── Saraksta kārtošana ────────────────────────────────────────────
  // Pogas un rindu kārtas atslēgas (data-o-name/-faction/-ballot) uzbūvē
  // bmv1.js::balsojumiTrackedHtml kopā ar tabulu. Te tikai pārliek <tbody>
  // rindas; pogas paliek tās pašas, tāpēc fokuss paliek uz nospiestās.
  var SORT_KEY = { name: 'oName', faction: 'oFaction', ballot: 'oBallot' };
  elById('votes-archive-cards').addEventListener('click', function(e) {
    var btn = e.target.closest && e.target.closest('.vote-sort-btn');
    if (!btn) return;
    var box = btn.closest('.vote-tracked');
    var tbody = box && box.querySelector('tbody');
    var key = SORT_KEY[btn.dataset.sort];
    if (!tbody || !key) return;
    var rows = Array.prototype.slice.call(tbody.rows);
    rows.sort(function(a, b) { return Number(a.dataset[key]) - Number(b.dataset[key]); });
    rows.forEach(function(r) { tbody.appendChild(r); });
    box.querySelectorAll('.vote-sort-btn').forEach(function(b) {
      b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
    });
  });

  // ── Kvadrātiņš → deputāts (viens kopīgs lodziņš #seat-pop) ────────
  // Plāns 2026-10-16 § Task 2b (Astra #4). Stāvoklis: aktīvais kvadrātiņš +
  // veids. Pele (hover ierīcē UN pointerType 'mouse') atver, uzbraucot;
  // klikšķis ar peli → profils. Pieskāriens/pildspalva atver lodziņu ar saiti
  // «Profils →» un NEnavigē. popover="auto": Esc un pieskāriens citur aizver
  // pārlūks pats; `toggle` notīra stāvokli. Bez {source} atbalsta lodziņš
  // atveras ekrāna vidū — apzināti bez JS pozicionēšanas.
  var seatPop = document.getElementById('seat-pop');
  var popState = { seat: null, mode: null, timer: null };
  var lastPointer = '';
  var canHover = window.matchMedia ? window.matchMedia('(hover: hover) and (pointer: fine)') : null;
  var SEAT_SEL = '.vote-seat[data-p], .vote-mseat[data-p]';

  function clearPopTimer() {
    if (popState.timer) { clearTimeout(popState.timer); popState.timer = null; }
  }
  function resetPopState() {
    clearPopTimer();
    if (popState.seat) popState.seat.classList.remove('is-seat-active');
    popState.seat = null;
    popState.mode = null;
  }
  function seatPopClose() {
    if (seatPop && seatPop.matches && seatPop.matches(':popover-open')) seatPop.hidePopover();
    resetPopState();
  }
  function seatInfo(seat) {
    var card = seat.closest('.vote-card');
    if (!card || !window.balsojumiSeatInfo) return null;
    var vid = card.id.slice('vote-'.length);
    var info = window.balsojumiSeatInfo(vid, seat.dataset.p);
    if (info) info.vid = vid;
    return info;
  }
  function fillPop(info, pid) {
    var name = document.createElement('p');
    name.className = 'seat-pop-name';
    name.textContent = info.name;
    var meta = document.createElement('p');
    meta.className = 'seat-pop-meta';
    meta.textContent = info.faction + ' · ' + info.ballot;
    seatPop.replaceChildren(name, meta);
    if (info.profileUrl) {
      var a = document.createElement('a');
      a.className = 'seat-pop-link';
      a.href = info.profileUrl;
      a.textContent = 'Profils →';
      seatPop.appendChild(a);
    }
    seatPop.dataset.vid = info.vid;
    seatPop.dataset.pid = pid;
  }
  function openSeat(seat, mode) {
    clearPopTimer();
    var open = seatPop.matches(':popover-open');
    if (open && popState.seat === seat) { popState.mode = mode; return; }
    var info = seatInfo(seat);
    if (!info) return;
    // Atvērtam lodziņam atkārtots showPopover enkuru NEpārceļ — vispirms aizver.
    if (open) seatPop.hidePopover();
    resetPopState();
    fillPop(info, seat.dataset.p);
    try { seatPop.showPopover({ source: seat }); } catch (err) { seatPop.showPopover(); }
    popState.seat = seat;
    popState.mode = mode;
    seat.classList.add('is-seat-active');
  }
  function scheduleClose() {
    if (popState.mode !== 'hover') return;
    clearPopTimer();
    popState.timer = setTimeout(seatPopClose, 200);
  }

  if (seatPop && seatPop.showPopover) {
    var cards = elById('votes-archive-cards');
    cards.addEventListener('pointerdown', function(e) { lastPointer = e.pointerType || ''; });
    cards.addEventListener('pointerover', function(e) {
      var seat = e.target.closest && e.target.closest(SEAT_SEL);
      if (!seat || e.pointerType !== 'mouse' || !canHover || !canHover.matches) return;
      openSeat(seat, 'hover');
    });
    cards.addEventListener('pointerout', function(e) {
      if (e.pointerType !== 'mouse') return;
      var seat = e.target.closest && e.target.closest(SEAT_SEL);
      if (seat && seat === popState.seat) scheduleClose();
    });
    cards.addEventListener('click', function(e) {
      var seat = e.target.closest && e.target.closest(SEAT_SEL);
      if (!seat) return;
      var pointer = e.pointerType || lastPointer;
      if (pointer === 'mouse') {
        var info = seatInfo(seat);
        if (info && info.profileUrl) { location.href = info.profileUrl; return; }
      }
      openSeat(seat, 'tap');
    });
    // Kursors uz paša lodziņa (lai var noklikšķināt saiti) aizvēršanu atceļ.
    seatPop.addEventListener('pointerover', clearPopTimer);
    seatPop.addEventListener('pointerout', function(e) {
      if (e.pointerType === 'mouse' && !seatPop.contains(e.relatedTarget)) scheduleClose();
    });
    seatPop.addEventListener('toggle', function(e) {
      if (e.newState === 'closed' && !seatPop.matches(':popover-open')) resetPopState();
    });
  }

  // Vienas sēdes dienas atlase (mēnesis + sēde), visus citus filtrus notīrot.
  // Lieto #vote- dziļās saites mašīna; applyFilters sauc izsaucējs.
  function selectSessionDay(dateStr) {
    clearAllVoteFilters();
    voteSearchQuery = '';
    if (voteSearch) voteSearch.value = '';
    if (monthApi) monthApi.setSelection([String(dateStr).substring(0, 7)]);
    sessionApi.setSelection([dateStr]);
    applySessionOptionVisibility();
  }

  // Iezīmē #vote-N kartīti, ja tā ir lapā; true = atrasta (stāvoklis → done).
  // Sauc tikai voteHashStep pēc kartīšu ievietošanas.
  function runVoteHashScroll() {
    if (voteHash.state === 'done') return false;
    var target = document.getElementById(location.hash.slice(1));
    if (!target) return false;
    voteHash.state = 'done';
    target.style.outline = '2px solid var(--accent)';
    target.style.outlineOffset = '4px';
    setTimeout(function() { target.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, 100);
    return true;
  }

  // ── Filtri URL adresē ─────────────────────────────────────────────
  // Lai atrasto var nosūtīt: ?q=…&tema=…&deputats=…&menesis=…&sede=…&dalitie=1
  // (vairākas vērtības = atkārtots parametrs). replaceState, ne pushState —
  // katrs meklēšanas taustiņš nedrīkst kļūt par soli «Atpakaļ» vēsturē.
  // Citi parametri un #vote- enkurs paliek neskarti.
  var URL_SELECTS = [
    ['tema', topicApi, selectedTopics],
    ['deputats', deputyApi, selectedDeputies],
    ['menesis', monthApi, selectedMonths],
    ['sede', sessionApi, selectedSessions],
  ];

  function writeFiltersToUrl() {
    if (!window.history || !history.replaceState) return;
    var p = new URLSearchParams(location.search);
    p.delete('q');
    p.delete('dalitie');
    URL_SELECTS.forEach(function(row) {
      p.delete(row[0]);
      row[2].forEach(function(v) { p.append(row[0], v); });
    });
    if (voteSearchQuery) p.set('q', voteSearchQuery);
    if (splitOnly) p.set('dalitie', '1');
    var qs = p.toString();
    history.replaceState(null, '', location.pathname + (qs ? '?' + qs : '') + location.hash);
  }

  // Lasa TIKAI vērtības, kas ir opciju sarakstā: veca saite vai pārdēvēta
  // tēma paliek noklusējumā, nevis rāda «0 balsojumu» bez redzama iemesla.
  function readFiltersFromUrl() {
    var p = new URLSearchParams(location.search);
    URL_SELECTS.forEach(function(row) {
      if (!row[1]) return;
      var known = {};
      row[1].options.forEach(function(o) { known[o.dataset.value] = true; });
      row[1].setSelection(p.getAll(row[0]).filter(function(v) { return known[v]; }));
    });
    dropSessionsOutsideMonths();
    applySessionOptionVisibility();
    voteSearchQuery = (p.get('q') || '').trim();
    if (voteSearch) voteSearch.value = voteSearchQuery;
    splitOnly = p.get('dalitie') === '1';
    if (splitToggle) {
      splitToggle.classList.toggle('active', splitOnly);
      splitToggle.setAttribute('aria-pressed', splitOnly ? 'true' : 'false');
    }
  }

  // Single rendering path — populate the archive shell immediately. bmv1.js is
  // loaded synchronously above, so window.balsojumiArchiveRender exists here.
  // Filtri no adreses tiek uzlikti PIRMS tā, tāpēc ielāde renderē vienreiz.
  readFiltersFromUrl();
  renderArchive(true);
})();
