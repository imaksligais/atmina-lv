// sav1.js — saites lapas (politiķu savstarpējo saišu grafs) klienta puses skripts.
//   1) D3 spēka grafs (mezgli = politiķi, līnijas = spriedzes/balsojumi/kopīgās tēmas),
//   2) detaļu panelis (mezgla/līnijas klikšķis → pozīcijas/saites/balsojumi/pretrunas).
//
// Kopš 2026-10-18 šo failu lapas sākumā NEielādē: assets/ssv1.js pēc pogas «Rādīt
// visu tīklu» ielādē assets/d3.v7.min.js (pašmitināts kopš 2026-08-15), tad šo
// failu, tad data/saites-graph.json { graph, tensions, contrasByPid } un izsauc
// window.atminaSaitesGraph.open(data). Mazie dati (partyColors, tipu etiķetes un
// žetoni) paliek inline <script type="application/json" id="saites-data">.
//
// claims + mazā {pid: vote_count} karte lēni ielādējas no data/saites-data.json
// pirmajā detaļu atvēršanā. Smagais balsojumu reģistrs (votesMeta/votesByPid) dzīvo
// data/saites-votes.json un ielādējas tikai tad, kad atver "Balsojumi" sekciju —
// tā izplatītais detaļu-atvēršanas fetch paliek ~6× vieglāks. Sk. _emit_saites_json.

// ── Mazie lapas dati no inline JSON bloka; grafa dati — open(data) ──
var _saitesDataEl = document.getElementById('saites-data');
var _saitesJson = _saitesDataEl ? JSON.parse(_saitesDataEl.textContent) : {};
let graphData = { nodes: [], links: [] };
let tensionsData = [];
let contrasByPid = {};
// Balsojumu sakritība pa mezgliem: {pid: {top: [[pid, agree, total]…], bottom: […]}}
// (links.py, tā pati _vote_alignment_for kā profilā). Zīmē tikai izvēlētajam.
let voteAlign = {};
// Izcelšanas stāvoklis pārdzīvo grafa pārbūvi (resize).
var _hl = { nodeId: null, party: null };
const _partyColorsData = _saitesJson.partyColors || {};
// Spriedžu tipu etiķetes un žetonu klases — no servera (TENSION_TYPE_LV /
// TENSION_BADGE, src/render/_common/constants.py), ne savs kartējums.
const _tensionLabels = _saitesJson.tensionLabels || {};
const _tensionBadges = _saitesJson.tensionBadges || {};

// Lēni ielādētās kešatmiņas (kods, ne dati — sākotnēji tukši, aizpildās ar fetch).
let claimsByPid = {};
let votesCount = {};
let votesMeta = [];
let votesByPid = {};
let _saitesDataLoaded = false;
let _saitesDataPromise = null;
let _saitesVotesLoaded = false;
let _saitesVotesPromise = null;

let _saitesGraphOpened = false;
window.atminaSaitesGraph = {
  // Vienreiz: otrs izsaukums neko nedara (poga pēc atvēršanas paslēpta).
  open: function(data) {
    if (_saitesGraphOpened) return;
    _saitesGraphOpened = true;
    data = data || {};
    graphData = data.graph || { nodes: [], links: [] };
    tensionsData = data.tensions || [];
    contrasByPid = data.contrasByPid || {};
    voteAlign = graphData.voteAlign || {};
    _initSaitesGraph();
  }
};

function _initSaitesGraph() {
  // ── D3 Force Graph ──
  function cssVar(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
  var _themeRestyle = null;
  var container = document.getElementById('graph-container');
  var svg = d3.select('#graph-svg');
  if (!container || !svg.node() || !graphData || !graphData.nodes.length) {
    // No data — hide graph
    if (container) container.style.display = 'none';
  } else {
    initGraph();
    // Pārbūvē tikai, ja mainās platums: telefonā adreses josla ritinot maina
    // augstumu un agrāk izmeta izvēli un visu izkārtojumu.
    var _lastW = container.clientWidth;
    window.addEventListener('resize', function() {
      if (container.clientWidth === _lastW) return;
      _lastW = container.clientWidth;
      svg.selectAll('*').remove();
      initGraph();
    });
  }

  function initGraph() {
    svg.selectAll('*').remove();

    var width = container.clientWidth;
    var height = container.clientHeight;
    var isMobile = window.innerWidth <= 768;
    var mobileScale = isMobile ? 0.7 : 1;

    var g = svg.append('g');

    // Zoom + pan
    var zoom = d3.zoom()
      .scaleExtent([0.3, 4])
      .on('zoom', function(event) { g.attr('transform', event.transform); });
    svg.call(zoom);

    // Deep copy nodes and links for simulation
    var simNodes = graphData.nodes.map(function(n) { return Object.assign({}, n); });
    var simLinks = graphData.links.map(function(l) { return Object.assign({}, l); });

    // Party colors — single source of truth: parties.color (DB), emitted
    // server-side via the #saites-data block (src.coalition.party_color_map). Unmapped parties fall back
    // to --text-muted below.
    var partyColors = _partyColorsData;

    // Party cluster positions — arrange every party present in the graph in a
    // circle (derived from the node data, not the colour map, so parties without
    // an explicit brand colour still cluster instead of collapsing to centre).
    var partyList = Array.from(new Set(simNodes.map(function(n) { return n.party; }).filter(Boolean)));
    var partyAngle = {};
    partyList.forEach(function(p, i) { partyAngle[p] = (2 * Math.PI * i) / partyList.length; });
    var clusterR = Math.min(width, height) * 0.28;

    // Node radius based on claims count (sqrt scale, min 6, max 25)
    function nodeRadius(d) {
      return Math.min(25, Math.max(6, Math.sqrt(d.claims || 1) * 3)) * mobileScale;
    }

    // Force simulation
    var simulation = d3.forceSimulation(simNodes)
      .force('link', d3.forceLink(simLinks).id(function(d) { return d.id; }).distance(isMobile ? 100 : 160).strength(0.3))
      .force('charge', d3.forceManyBody().strength(isMobile ? -150 : -300))
      .force('center', d3.forceCenter(width / 2, height / 2).strength(0.05))
      .force('clusterX', d3.forceX(function(d) {
        var a = partyAngle[d.party]; return a !== undefined ? width/2 + Math.cos(a) * clusterR : width/2;
      }).strength(0.15))
      .force('clusterY', d3.forceY(function(d) {
        var a = partyAngle[d.party]; return a !== undefined ? height/2 + Math.sin(a) * clusterR : height/2;
      }).strength(0.15))
      .force('collision', d3.forceCollide().radius(function(d) { return nodeRadius(d) + 6; }))
      .alphaDecay(0.015);

    // Active link type filters
    var activeFilters = window._graphActiveFilters ||
      new Set(['uzbrukums', 'spriedze', 'atbalsts', 'politikas nostāju konflikts', 'shared_topic']);
    // Detaļu panelis lasa to pašu filtru (activeTensionTypes, visibleTensions).
    window._graphActiveFilters = activeFilters;

    // Link stroke width
    function linkWidth(d) {
      if (d.type === 'tension') return 2.5;
      if (d.type === 'support') return 2;
      return Math.max(0.5, Math.min((d.weight || 1) * 0.4, 2));
    }

    // Link color
    function linkColor(d) {
      if (d.type === 'tension') {
        if (d.tension_type === 'spriedze') return cssVar('--yellow');
        if (d.tension_type === 'politikas nostāju konflikts') return cssVar('--accent');  // badge-blue tonis
        return cssVar('--red-bright');  // uzbrukums
      }
      if (d.type === 'support') return cssVar('--green');
      if (d.type === 'shared_topic') return 'rgba(100,116,139,0.35)';
      return cssVar('--graph-link-default');
    }

    // Filter visibility
    function linkVisible(d) {
      return activeFilters.has(d.tension_type);
    }

    // Draw links — with invisible wider hit area for clickability
    var linkGroup = g.append('g').selectAll('g').data(simLinks).join('g');
    // Invisible wide line for easier clicking
    linkGroup.append('line')
      .attr('stroke', 'transparent')
      .attr('stroke-width', 12)
      .style('cursor', function(d) { return (d.type === 'tension' || d.type === 'support' || d.type === 'shared_topic') ? 'pointer' : 'default'; });
    // Visible line
    linkGroup.append('line')
      .attr('stroke', linkColor)
      .attr('stroke-width', linkWidth)
      .attr('stroke-dasharray', function(d) {
        if (d.type === 'shared_topic') return '4,3';
        return 'none';
      })
      .style('pointer-events', 'none');
    var link = linkGroup;

    // Apply filter visibility
    function applyLinkFilters() {
      link.style('display', function(d) {
        return linkVisible(d) ? '' : 'none';
      });
    }
    applyLinkFilters();
    window._graphApplyFilters = function() { applyLinkFilters(); applyHighlight(); };

    // Balsojumu līnijas: slānis zem mezgliem, saturs tikai izvēlētajam mezglam.
    var voteLayer = g.append('g').attr('class', 'vote-layer');
    var nodeById = {};
    simNodes.forEach(function(n) { nodeById[n.id] = n; });
    function votePartners(id) {
      var va = voteAlign[id] || voteAlign[String(id)];
      if (!va) return [];
      var out = [];
      [['top', va.top || []], ['bottom', va.bottom || []]].forEach(function(pair) {
        pair[1].forEach(function(r) {
          var other = nodeById[r[0]];
          if (!other) return;
          out.push({ type: 'vote', rank: pair[0], source: nodeById[id], target: other,
                     agree: r[1], total: r[2], agree_pct: Math.round(r[1] * 100 / r[2]) });
        });
      });
      return out;
    }
    window._graphVotePartners = votePartners;
    var voteLines = voteLayer.selectAll('g');
    function drawVoteLines() {
      var data = (_hl.nodeId != null && nodeById[_hl.nodeId]) ? votePartners(_hl.nodeId) : [];
      voteLines = voteLayer.selectAll('g').data(data, function(d) { return d.rank + '-' + d.target.id; })
        .join(function(enter) {
          var gg = enter.append('g').attr('class', function(d) { return 'vote-line vote-' + d.rank; });
          gg.append('line').attr('stroke', 'transparent').attr('stroke-width', 14).style('cursor', 'pointer');
          gg.append('line').style('pointer-events', 'none').attr('stroke-dasharray', '5,3');
          return gg;
        });
      voteLines.select('line:nth-child(2)')
        .attr('stroke', function(d) { return d.rank === 'top' ? cssVar('--purple') : cssVar('--text-muted'); })
        .attr('stroke-width', 2);
      voteLines.on('click', function(event, d) {
        event.stopPropagation();
        showLinkDetail(d);
      });
      positionVoteLines();
    }
    function positionVoteLines() {
      voteLines.selectAll('line')
        .attr('x1', function(d) { return d.source.x; })
        .attr('y1', function(d) { return d.source.y; })
        .attr('x2', function(d) { return d.target.x; })
        .attr('y2', function(d) { return d.target.y; });
    }

    // Filter button click handlers
    document.querySelectorAll('.link-filter-btn').forEach(function(btn) {
      if (btn.dataset.bound) return;
      btn.dataset.bound = '1';
      btn.addEventListener('click', function() {
        var type = btn.dataset.linkType;
        if (activeFilters.has(type)) {
          activeFilters.delete(type);
          btn.classList.remove('active');
          btn.setAttribute('aria-pressed', 'false');
        } else {
          activeFilters.add(type);
          btn.classList.add('active');
          btn.setAttribute('aria-pressed', 'true');
        }
        if (window._graphApplyFilters) window._graphApplyFilters();
        if (window._refreshNodeDetail) window._refreshNodeDetail();
      });
    });

    // Draw nodes
    var node = g.append('g')
      .selectAll('g')
      .data(simNodes)
      .join('g')
      .call(d3.drag()
        .on('start', function(event, d) {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', function(event, d) { d.fx = event.x; d.fy = event.y; })
        .on('end', function(event, d) {
          if (!event.active) simulation.alphaTarget(0);
          // Brief elastic settle so connected neighbors visibly wobble after release
          simulation.alpha(0.15).restart();
        })
      );

    // Node circles
    node.append('circle')
      .attr('r', nodeRadius)
      .attr('fill', function(d) { return partyColors[d.party] || cssVar('--text-muted'); })
      .attr('stroke', cssVar('--graph-node-stroke'))
      .attr('stroke-width', 1.5)
      .style('cursor', 'pointer')
      .style('filter', 'drop-shadow(0 0 3px ' + cssVar('--shadow-overlay') + ')');

    // Contradiction indicator — small warning dot at top-right of node
    node.filter(function(d) { return d.contradictions > 0; })
      .append('circle')
      .attr('r', function(d) { return Math.min(6, 3 + d.contradictions) * mobileScale; })
      .attr('cx', function(d) { return nodeRadius(d) * 0.65; })
      .attr('cy', function(d) { return -nodeRadius(d) * 0.65; })
      .attr('fill', cssVar('--red-bright'))
      .attr('stroke', 'var(--bg)')
      .attr('stroke-width', 1.5)
      .style('pointer-events', 'none');
    // Contradiction count label inside the dot
    node.filter(function(d) { return d.contradictions > 0; })
      .append('text')
      .text(function(d) { return d.contradictions; })
      .attr('x', function(d) { return nodeRadius(d) * 0.65; })
      .attr('y', function(d) { return -nodeRadius(d) * 0.65 + 1; })
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('fill', '#fff')
      .attr('font-size', function(d) { return (Math.min(6, 3 + d.contradictions) * mobileScale * 1.4) + 'px'; })
      .attr('font-weight', '700')
      .attr('font-family', 'system-ui, sans-serif')
      .style('pointer-events', 'none');

    // Node labels (surname)
    node.append('text')
      .attr('class', 'node-surname')
      .text(function(d) { return d.name.split(' ').pop(); })
      .attr('dy', function(d) { return nodeRadius(d) + 12; })
      .attr('text-anchor', 'middle')
      .attr('fill', cssVar('--graph-label'))
      .attr('font-size', isMobile ? '7px' : '9px')
      .attr('font-family', 'system-ui, sans-serif')
      .style('pointer-events', 'none');

    // ── Izcelšana: viena funkcija visiem stāvokļiem (2026-11-22) ──
    // Izvēlēts mezgls (klikšķis/pieskāriens) → viņš, kaimiņi un balsojumu
    // partneri; izvēlēta partija (leģenda) → tās mezgli. Hover (tikai ar peli)
    // rāda to pašu īslaicīgi, un mouseout atgriež izvēlēto stāvokli.
    var canHover = window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    function neighborSet(id) {
      var set = {}; set[id] = true;
      simLinks.forEach(function(l) {
        if (!linkVisible(l)) return;
        if (l.source.id === id) set[l.target.id] = true;
        if (l.target.id === id) set[l.source.id] = true;
      });
      votePartners(id).forEach(function(v) { set[v.target.id] = true; });
      return set;
    }
    function applyHighlight(focusId) {
      var id = focusId != null ? focusId : _hl.nodeId;
      if (id != null && !nodeById[id]) id = null;
      if (id != null) {
        var near = neighborSet(id);
        node.attr('opacity', function(n) { return near[n.id] ? 1 : 0.15; });
        link.attr('opacity', function(l) { return (l.source.id === id || l.target.id === id) ? 1 : 0.08; });
      } else if (_hl.party != null) {
        var p = _hl.party;
        node.attr('opacity', function(n) { return n.party === p ? 1 : 0.15; });
        link.attr('opacity', function(l) { return (l.source.party === p || l.target.party === p) ? 1 : 0.08; });
      } else {
        node.attr('opacity', 1);
        link.attr('opacity', 1);
      }
      node.select('circle')
        .attr('stroke', function(n) { return n.id === _hl.nodeId ? 'var(--accent)' : cssVar('--graph-node-stroke'); })
        .attr('stroke-width', function(n) { return n.id === _hl.nodeId ? 3 : 1.5; });
      if (focusId != null && focusId !== _hl.nodeId) {
        node.filter(function(n) { return n.id === focusId; }).select('circle')
          .attr('stroke', cssVar('--graph-node-stroke-hover')).attr('stroke-width', 2.5);
      }
    }
    window._graphSetParty = function(party) {
      _hl.party = party;
      _hl.nodeId = null;
      drawVoteLines();
      applyHighlight();
    };

    if (canHover) {
      node.on('mouseover', function(event, d) { applyHighlight(d.id); })
        .on('mouseout', function() { applyHighlight(); });
    }
    node.on('click', function(event, d) {
      event.stopPropagation();
      _hl.nodeId = d.id;
      drawVoteLines();
      applyHighlight();
      showNodeDetail(d);
    });

    // Link interactions — click to show detail in panel
    link.on('mouseover', function(event, d) {
      if (d.type === 'tension' || d.type === 'support' || d.type === 'shared_topic') {
        d3.select(this).select('line:nth-child(2)').attr('stroke-width', Math.max(linkWidth(d) * 2.5, 4));
      }
    })
    .on('mouseout', function(event, d) {
      d3.select(this).select('line:nth-child(2)').attr('stroke-width', linkWidth(d));
    })
    .on('click', function(event, d) {
      if (d.type !== 'tension' && d.type !== 'support' && d.type !== 'shared_topic') return;
      event.stopPropagation();
      _hl.nodeId = null;
      drawVoteLines();
      applyHighlight();
      showLinkDetail(d);
    });

    // Click empty space to deselect
    svg.on('click', function() {
      _hl.nodeId = null;
      drawVoteLines();
      applyHighlight();
      showEmptyDetail();
    });

    // Pēc pārbūves (resize) atjauno izvēli.
    drawVoteLines();
    applyHighlight();

    // Simulation tick
    simulation.on('tick', function() {
      link.selectAll('line')
        .attr('x1', function(d) { return d.source.x; })
        .attr('y1', function(d) { return d.source.y; })
        .attr('x2', function(d) { return d.target.x; })
        .attr('y2', function(d) { return d.target.y; });
      node.attr('transform', function(d) { return 'translate(' + d.x + ',' + d.y + ')'; });
      positionVoteLines();
    });

    // Re-read tokens on theme switch — the persistent graph bakes resolved
    // colors into SVG attributes, so re-apply the styling pass (positions kept).
    if (_themeRestyle) document.removeEventListener('atmina:themechange', _themeRestyle);
    _themeRestyle = function() {
      link.select('line:nth-child(2)').attr('stroke', linkColor);
      node.select('circle')
        .attr('fill', function(d) { return partyColors[d.party] || cssVar('--text-muted'); })
        .attr('stroke', function(d) { return _hl.nodeId === d.id ? 'var(--accent)' : cssVar('--graph-node-stroke'); })
        .style('filter', 'drop-shadow(0 0 3px ' + cssVar('--shadow-overlay') + ')');
      node.selectAll('text.node-surname').attr('fill', cssVar('--graph-label'));
      drawVoteLines();
    };
    document.addEventListener('atmina:themechange', _themeRestyle);
  }

  // Partiju leģenda: spiediens izceļ partijas mezglus, otrs noņem.
  document.querySelectorAll('.graph-party-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var on = btn.getAttribute('aria-pressed') !== 'true';
      document.querySelectorAll('.graph-party-btn').forEach(function(o) { o.setAttribute('aria-pressed', 'false'); });
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
      if (window._graphSetParty) window._graphSetParty(on ? btn.dataset.party : null);
      if (on) showEmptyDetail();
    });
  });

  // ── Detail pane (inline, always visible) ──
  var detailEmpty = document.getElementById('detail-empty');
  var detailContent = document.getElementById('detail-content');

  // Deleģēts klikšķis detaļu paneļa konteinerī: sekciju pogas nes data-section.
  // Inline onclick, kas injicēts caur innerHTML, ir kluss miris strict CSP režīmā,
  // tāpēc pārslēdzamies uz deleģēšanu (viens klausītājs uz konteinera).
  if (detailContent) {
    detailContent.addEventListener('click', function(e) {
      var btn = e.target.closest('.detail-stat-btn[data-section]');
      if (!btn || !detailContent.contains(btn)) return;
      renderNodeSection(btn.dataset.section);
    });
  }

  function escHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // Redzamais datums DD.MM.YYYY — kopīgais window.atminaLvDate (assets/sgv1.js;
  // sav1 ielādē ssv1.js pēc pogas, tātad pēc sgv1).
  var lvDate = window.atminaLvDate;
  // Skaitlis ar tūkstošu atstarpi un LV skaitļa saskaņa — tas pats sgv1.js.
  var fmtN = window.atminaFmtN;
  var lvPlural = window.atminaLvPlural;

  function badgeClass(type) {
    return _tensionBadges[type] || '';
  }

  function typeLabel(type) {
    return _tensionLabels[type] || type || '';
  }

  // ── Grafa tipu filtrs ↔ detaļu panelis ───────────────────────────
  // Līdz 2026-08-15 panelis filtru neredzēja: čipi slēpa SVG līnijas, bet
  // mezgla klikšķis vienmēr atvēra visas pozīcijas un neatlasītu saišu
  // sarakstu. Filtrs un panelis izskatās kā viens rīks, tāpēc tiem jārāda
  // viens un tas pats. _graphActiveFilters nav, ja grafs nav inicializēts
  // (nav datu) — tad visu rāda nefiltrētu.
  var TENSION_TYPES = ['uzbrukums', 'spriedze', 'atbalsts', 'politikas nostāju konflikts'];

  // Pozīciju griesti panelī. Mediānajam politiķim ir 12 pozīcijas, bet
  // maksimums ir 421 — sānu panelis nav pārlūkošanas saskarne, un pilna lapa
  // tam jau ir (politiki/<slug>.html). Pārpalikums aiziet uz profilu, nevis
  // uz "Rādīt vairāk" pogu. Payload NETIEK apgriezts: kopīgās tēmas saite
  // (renderTopicClaims) atlasa pozīcijas no visas vēstures.
  var POSITIONS_CAP = 20;

  function activeTensionTypes() {
    var f = window._graphActiveFilters;
    if (!f) return null;
    return TENSION_TYPES.filter(function(t) { return f.has(t); });
  }

  function visibleTensions(list) {
    var f = window._graphActiveFilters;
    if (!f) return list;
    return list.filter(function(t) { return f.has(t.tension_type); });
  }

  // Avota saite tikai uz http(s) — servera `safe_url` filtra spogulis
  // (src/render/_common/filters.py; tas pats pzv1.js safeHttpUrl).
  function safeHttpUrl(u) {
    var s = u == null ? '' : String(u).trim();
    return /^https?:\/\//i.test(s) ? s : '';
  }

  // Generate source link — external URL or fallback to our site
  function sourceLink(url, fallbackSlug, fallbackLabel) {
    url = safeHttpUrl(url);
    if (url) {
      var isX = url.indexOf('x.com/') !== -1 || url.indexOf('twitter.com/') !== -1;
      var label = isX ? 'X/Twitter &rarr;' : 'Avots &rarr;';
      return '<a href="' + escHtml(url) + '" target="_blank" rel="noopener">' + label + '</a>';
    }
    if (fallbackSlug) {
      return '<a href="politiki/' + escHtml(fallbackSlug) + '.html">' + escHtml(fallbackLabel || 'Profils') + ' &rarr;</a>';
    }
    return '';
  }


  // Balsojumu sakritības saraksts panelī: tās pašas 3 + 3 rindas, ko tīklā
  // zīmē raustītās līnijas (telefonā līnijas ir sīkas — saraksts ir galvenais).
  function voteAlignHtml(d) {
    var partners = window._graphVotePartners ? window._graphVotePartners(d.id) : [];
    if (!partners.length) return '';
    var html = '';
    [['top', 'Visbiežāk balso vienādi'], ['bottom', 'Visretāk balso vienādi']].forEach(function(g) {
      var rows = partners.filter(function(v) { return v.rank === g[0]; });
      if (!rows.length) return;
      html += '<p class="detail-section-title">' + g[1] + '</p><ul class="detail-vote-list">';
      rows.forEach(function(v) {
        html += '<li><a href="politiki/' + escHtml(v.target.slug) + '.html#saites">' + escHtml(v.target.name) + '</a>' +
          '<span class="detail-vote-n">' + v.agree_pct + ' % · ' + fmtN(v.agree) + '/' + fmtN(v.total) + '</span></li>';
      });
      html += '</ul>';
    });
    return html;
  }

  window.showEmptyDetail = function() {
    detailEmpty.hidden = false;
    detailContent.hidden = true;
  };

  var currentDetailNode = null;

  window.renderNodeSection = function(section) {
    if (!currentDetailNode) return;
    var d = currentDetailNode;
    var container = document.getElementById('detail-section-content');
    if (!container) return;

    // Update active tab
    document.querySelectorAll('.detail-stat-btn').forEach(function(btn) {
      var on = btn.dataset.section === section;
      btn.classList.toggle('active', on);
      btn.setAttribute('aria-pressed', String(on));
    });

    if (section === 'pozicijas') {
      // Serveris tās jau sakārtojis jaunākās pirmās (links.py).
      var allClaims = claimsByPid[d.id] || claimsByPid[String(d.id)] || [];
      if (allClaims.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);">Nav pozīciju.</p>';
        return;
      }
      var claims = allClaims.slice(0, POSITIONS_CAP);
      var html = '';
      if (allClaims.length > claims.length) {
        html += '<p class="detail-filter-note">Rāda ' + claims.length + ' jaunākās no ' +
          fmtN(allClaims.length) + ' · <a href="politiki/' + escHtml(d.slug) + '.html">Visas profilā &rarr;</a></p>';
      }
      claims.forEach(function(c) {
        html += '<div class="detail-link-card">' +
          '<div class="panel-tension-header">' +
            '<span class="topic-tag">' + escHtml(c.topic) + '</span>' +
            '<span style="color:var(--text-muted);font-size:0.7rem;margin-left:auto;white-space:nowrap;">' + escHtml(lvDate(c.date)) + '</span>' +
          '</div>' +
          '<div class="link-desc">' + escHtml(c.stance) + '</div>' +
          '<div class="link-footer">' +
            sourceLink(c.source_url, d.slug, d.name) +
            '<span style="color:var(--text-muted);font-size:0.75rem;">tic. ' + (c.confidence || 0).toFixed(1).replace('.', ',') + '</span>' +
          '</div>' +
        '</div>';
      });
      container.innerHTML = html;

    } else if (section === 'saites') {
      var all = tensionsData.filter(function(t) {
        return t.source_name === d.name || t.target_name === d.name;
      });
      var matching = visibleTensions(all);
      var votesHtml = voteAlignHtml(d);
      if (all.length === 0) {
        container.innerHTML = '<p class="detail-empty-note">Šim politiķim vēl nav ierakstītu saikņu.</p>' +
          (votesHtml ? votesHtml : '<button type="button" class="detail-stat-btn" data-section="pozicijas">Skatīt pozīcijas</button>');
        return;
      }
      if (matching.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);">Nav saišu ar izvēlētajiem tipiem. ' +
          'Šim politiķim ir ' + fmtN(all.length) + ' cita tipa ' + lvPlural(all.length, 'saite', 'saites') + ' — ieslēdz tipus augšā.</p>' + votesHtml;
        return;
      }
      var html = votesHtml ? votesHtml + '<p class="detail-section-title">Saiknes</p>' : '';
      if (matching.length < all.length) {
        html += '<p class="detail-filter-note">Rāda ' + fmtN(matching.length) + ' no ' + fmtN(all.length) + ' ' +
          lvPlural(all.length, 'saites', 'saitēm') + ' · ' + activeTensionTypes().map(typeLabel).join(', ') + '</p>';
      }
      matching.forEach(function(t) {
        html += '<div class="detail-link-card">' +
          '<div class="panel-tension-header">' +
            '<span class="badge ' + badgeClass(t.tension_type) + '">' + escHtml(typeLabel(t.tension_type)) + '</span>' +
            '<span class="topic-tag">' + escHtml(t.topic) + '</span>' +
          '</div>' +
          '<div class="link-parties">' +
            '<strong>' + escHtml(t.source_name) + '</strong>' +
            '<span class="link-arrow">&rarr;</span>' +
            '<strong>' + escHtml(t.target_name) + '</strong>' +
          '</div>' +
          '<div class="link-desc">' + escHtml(t.description || '') + '</div>' +
          '<div class="link-footer">' +
            '<div>' +
              sourceLink(t.source_url, t.source_slug, t.source_name) +
              (t.target_url ? ' &middot; ' + sourceLink(t.target_url, t.target_slug, t.target_name) : '') +
            '</div>' +
            (t.date ? '<span style="color:var(--text-muted);font-size:0.8rem;">' + escHtml(lvDate(t.date)) + '</span>' : '') +
          '</div>' +
        '</div>';
      });
      container.innerHTML = html;

    } else if (section === 'balsojumi') {
      // The heavy vote ledger is a separate sidecar — fetch on first open, re-run.
      if (!_saitesVotesLoaded) {
        container.innerHTML = '<p style="color:var(--text-muted);padding:1rem;">Ielādē balsojumus…</p>';
        loadSaitesVotes()
          .then(function() { renderNodeSection('balsojumi'); })
          .catch(function() { container.innerHTML = '<p style="color:var(--text-muted);">Neizdevās ielādēt balsojumus.</p>'; });
        return;
      }
      var votes = votesByPid[d.id] || votesByPid[String(d.id)] || [];
      if (votes.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);">Nav balsojumu.</p>';
        return;
      }
      function voteBadgeClass(v) {
        if (v === 'Par') return 'badge-green';
        if (v === 'Pret') return 'badge-red';
        if (v === 'Atturas') return 'badge-yellow';
        return '';
      }
      var html = '';
      votes.forEach(function(pair) {
        var meta = votesMeta[pair[0]];
        if (!meta) return;
        var voteStr = pair[1];
        html += '<div class="detail-link-card">' +
          '<div class="panel-tension-header">' +
            '<span class="badge ' + voteBadgeClass(voteStr) + '">' + escHtml(voteStr || '?') + '</span>' +
            (meta.topic ? '<span class="topic-tag">' + escHtml(meta.topic) + '</span>' : '') +
            '<span style="color:var(--text-muted);font-size:0.7rem;margin-left:auto;white-space:nowrap;">' + escHtml(lvDate(meta.date)) + '</span>' +
          '</div>' +
          '<div class="link-desc">' + escHtml(meta.motif) + '</div>' +
          '<div class="link-footer">' +
            '<a href="balsojumi.html#vote-' + meta.id + '">Balsojums &rarr;</a>' +
            (safeHttpUrl(meta.url) ? '<a href="' + escHtml(safeHttpUrl(meta.url)) + '" target="_blank" rel="noopener" style="color:var(--text-muted);font-size:0.75rem;">Saeima &rarr;</a>' : '') +
          '</div>' +
        '</div>';
      });
      container.innerHTML = html;

    } else if (section === 'pretrunas') {
      var contras = contrasByPid[d.id] || contrasByPid[String(d.id)] || [];
      if (contras.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);">Nav pretrunu.</p>';
        return;
      }
      var html = '';
      contras.forEach(function(c) {
        var sevBadge = c.severity === 'direct_contradiction' ? 'badge-red' :
                       c.severity === 'reversal' ? 'badge-yellow' : '';
        var sevLabel = c.severity === 'direct_contradiction' ? 'Tieša pretruna' :
                       c.severity === 'reversal' ? 'Nostājas maiņa' : 'Neliela novirze';
        html += '<div class="detail-link-card" style="border-left:3px solid var(--red-bright);">' +
          '<div class="panel-tension-header">' +
            '<span class="badge ' + sevBadge + '">' + escHtml(sevLabel) + '</span>' +
            '<span class="topic-tag">' + escHtml(c.topic) + '</span>' +
            '<span style="color:var(--text-muted);font-size:0.7rem;margin-left:auto;white-space:nowrap;">' + escHtml(lvDate(c.date)) + '</span>' +
          '</div>' +
          '<div class="link-desc">' + escHtml(c.summary) + '</div>';
        if (c.old_stance || c.new_stance) {
          var oldLbl = c.old_label || 'Iepriekš';
          var newLbl = c.new_label || 'Pašlaik';
          html += '<div style="margin-top:0.4rem;font-size:0.8rem;">';
          if (c.old_stance) html += '<div style="color:var(--text-muted);margin-bottom:0.2rem;"><span style="opacity:0.5;">' + escHtml(oldLbl) + ':</span> ' + escHtml(c.old_stance) +
            (safeHttpUrl(c.old_url) ? ' <a href="' + escHtml(safeHttpUrl(c.old_url)) + '" target="_blank" rel="noopener" style="color:var(--accent);font-size:0.75rem;">avots</a>' : '') + '</div>';
          if (c.new_stance) html += '<div style="color:var(--text-muted);"><span style="opacity:0.5;">' + escHtml(newLbl) + ':</span> ' + escHtml(c.new_stance) +
            (safeHttpUrl(c.new_url) ? ' <a href="' + escHtml(safeHttpUrl(c.new_url)) + '" target="_blank" rel="noopener" style="color:var(--accent);font-size:0.75rem;">avots</a>' : '') + '</div>';
          html += '</div>';
        }
        if (c.context_note) {
          html += '<div style="margin-top:0.4rem;padding:6px 10px;border-left:2px solid var(--border-soft);background:var(--surface-lift);font-size:0.72rem;font-style:italic;color:var(--text-muted);"><span style="opacity:0.6;font-style:normal;letter-spacing:1px;text-transform:uppercase;font-size:0.6rem;">Konteksts</span><br>' + escHtml(c.context_note) + '</div>';
        }
        html += '</div>';
      });
      container.innerHTML = html;
    }
  };

  function loadSaitesData() {
    if (_saitesDataPromise) return _saitesDataPromise;
    _saitesDataPromise = fetch('data/saites-data.json')
      .then(function(r) { if (!r.ok) throw new Error('saites-data ' + r.status); return r.json(); })
      .then(function(data) {
        claimsByPid = data.claimsByPid || {};
        votesCount = data.votesCount || {};
        _saitesDataLoaded = true;
      })
      .catch(function(e) { _saitesDataPromise = null; throw e; });
    return _saitesDataPromise;
  }

  // The heavy vote ledger loads separately, only when a "Balsojumi" section opens.
  function loadSaitesVotes() {
    if (_saitesVotesPromise) return _saitesVotesPromise;
    _saitesVotesPromise = fetch('data/saites-votes.json')
      .then(function(r) { if (!r.ok) throw new Error('saites-votes ' + r.status); return r.json(); })
      .then(function(data) {
        votesMeta = data.meta || [];
        votesByPid = data.byPid || {};
        _saitesVotesLoaded = true;
      })
      .catch(function(e) { _saitesVotesPromise = null; throw e; });
    return _saitesVotesPromise;
  }

  // First detail open: show a loading state, fetch the lazy payload, re-run.
  function ensureSaitesData(retry) {
    detailEmpty.hidden = true;
    detailContent.hidden = false;
    detailContent.innerHTML = '<p style="color:var(--text-muted);padding:1rem;">Ielādē…</p>';
    loadSaitesData().then(retry).catch(function() {
      detailContent.innerHTML = '<p style="color:var(--text-muted);padding:1rem;">Neizdevās ielādēt datus. Pārlādē lapu.</p>';
    });
  }

  window.showNodeDetail = function(d, forceSection) {
    if (!_saitesDataLoaded) { ensureSaitesData(function() { window.showNodeDetail(d, forceSection); }); return; }
    currentDetailNode = d;
    detailEmpty.hidden = true;
    detailContent.hidden = false;

    var allTensions = tensionsData.filter(function(t) {
      return t.source_name === d.name || t.target_name === d.name;
    });
    var matching = visibleTensions(allTensions);
    var contras = contrasByPid[d.id] || contrasByPid[String(d.id)] || [];
    var voteN = votesCount[d.id] || votesCount[String(d.id)] || 0;

    // Sašaurināts tipu filtrs nozīmē, ka lietotājs pēta saites, nevis
    // pozīcijas — tad tā ir arī atvērtā cilne.
    // Lapa saucas «Saites», tāpēc panelis atveras uz saitēm (2026-11-22).
    var section = forceSection || 'saites';
    var saitesLabel = (matching.length < allTensions.length)
      ? fmtN(matching.length) + ' / ' + fmtN(allTensions.length)
      : fmtN(allTensions.length);

    var html = '<h3>' + escHtml(d.name) + '</h3>' +
      '<div class="detail-subtitle"><span class="party-tag">' + escHtml(d.party) + '</span>' +
        ' <a href="politiki/' + escHtml(d.slug) + '.html" style="color:var(--accent);font-size:0.8rem;margin-left:0.5rem;">Profils &rarr;</a>' +
      '</div>' +
      '<div class="detail-meta">' +
        '<button type="button" class="detail-stat-btn" data-section="pozicijas" aria-pressed="false"><strong>' + fmtN(d.claims) + '</strong> ' + lvPlural(d.claims, 'pozīcija', 'pozīcijas') + '</button>' +
        '<button type="button" class="detail-stat-btn" data-section="saites" aria-pressed="false"><strong>' + saitesLabel + '</strong> ' + lvPlural(allTensions.length, 'saite', 'saites') + '</button>' +
        (voteN > 0 ? '<button type="button" class="detail-stat-btn" data-section="balsojumi" aria-pressed="false" style="border-color:var(--purple);"><strong style="color:var(--purple);">' + fmtN(voteN) + '</strong> ' + lvPlural(voteN, 'balsojums', 'balsojumi') + '</button>' : '') +
        (contras.length > 0 ? '<button type="button" class="detail-stat-btn" data-section="pretrunas" aria-pressed="false" style="border-color:var(--red-bright);"><strong style="color:var(--red-bright);">' + fmtN(contras.length) + '</strong> ' + lvPlural(contras.length, 'pretruna', 'pretrunas') + '</button>' : '') +
      '</div>' +
      '<div id="detail-section-content"></div>';

    detailContent.innerHTML = html;
    // renderNodeSection uzliek .active pareizajai pogai (tāpēc augšā neviena
    // nav iezīmēta cieti).
    renderNodeSection(section);
  };

  // Filtra maiņa ar atvērtu paneli: pārzīmē to pašu cilni ar jaunajiem
  // skaitļiem, nevis atgriež lietotāju sākumā.
  window._refreshNodeDetail = function() {
    if (!currentDetailNode) return;
    var cur = document.querySelector('.detail-stat-btn.active');
    window.showNodeDetail(currentDetailNode, cur ? cur.dataset.section : undefined);
  };

  window.showLinkDetail = function(d) {
    if (!_saitesDataLoaded) { ensureSaitesData(function() { window.showLinkDetail(d); }); return; }
    detailEmpty.hidden = true;
    detailContent.hidden = false;

    var sourceName = d.source.name || '';
    var targetName = d.target.name || '';
    var sourceSlug = d.source.slug || '';
    var targetSlug = d.target.slug || '';

    var html = '';
    if (d.type === 'shared_topic') {
      var srcId = d.source.id;
      var tgtId = d.target.id;
      var sharedTopic = d.topic || '';

      html += '<p class="detail-section-title">Kopīga tēma</p>' +
        '<div class="detail-link-card" style="border-color:#64748b;">' +
          '<div class="panel-tension-header">' +
            '<span class="topic-tag">' + escHtml(sharedTopic) + '</span>' +
          '</div>' +
          '<div class="link-parties" style="font-size:1rem;margin:0.75rem 0;">' +
            '<a href="politiki/' + escHtml(sourceSlug) + '.html" style="color:var(--accent);">' + escHtml(sourceName) + '</a>' +
            '<span class="link-arrow" style="font-size:1.2rem;">&harr;</span>' +
            '<a href="politiki/' + escHtml(targetSlug) + '.html" style="color:var(--accent);">' + escHtml(targetName) + '</a>' +
          '</div>' +
          '<div class="link-desc">' + escHtml(d.label || '') + '</div>' +
        '</div>';

      // Show claims from both politicians on this topic
      function renderTopicClaims(pid, name, slug) {
        var claims = (claimsByPid[pid] || claimsByPid[String(pid)] || []).filter(function(c) {
          return c.topic === sharedTopic;
        });
        if (claims.length === 0) return '';
        var out = '<hr class="detail-divider">' +
          '<p class="detail-section-title"><a href="politiki/' + escHtml(slug) + '.html" style="color:var(--accent);">' + escHtml(name) + '</a></p>';
        claims.forEach(function(c) {
          out += '<div class="detail-link-card">' +
            '<div class="link-desc">' + escHtml(c.stance) + '</div>' +
            '<div class="link-footer">' +
              sourceLink(c.source_url, slug, name) +
              '<span style="color:var(--text-muted);font-size:0.75rem;">' + escHtml(lvDate(c.date)) + '</span>' +
            '</div>' +
          '</div>';
        });
        return out;
      }
      html += renderTopicClaims(srcId, sourceName, sourceSlug);
      html += renderTopicClaims(tgtId, targetName, targetSlug);
    } else if (d.type === 'vote') {
      // Balsojumu sakritība (tā pati kā profila Saites cilnē).
      var pct = d.agree_pct || 0;
      var rankLabel = d.rank === 'top' ? 'Visbiežāk balso vienādi' : 'Visretāk balso vienādi';
      html += '<p class="detail-section-title">Balsojumu sakritība</p>' +
        '<div class="detail-link-card">' +
          '<div class="link-parties" style="font-size:1rem;margin:0 0 0.75rem;">' +
            '<a href="politiki/' + escHtml(sourceSlug) + '.html#saites" style="color:var(--accent);">' + escHtml(sourceName) + '</a>' +
            '<span class="link-arrow" style="font-size:1.2rem;">&harr;</span>' +
            '<a href="politiki/' + escHtml(targetSlug) + '.html#saites" style="color:var(--accent);">' + escHtml(targetName) + '</a>' +
          '</div>' +
          '<p class="link-desc"><strong>' + pct + ' %</strong> · balsoja vienādi ' + fmtN(d.agree) + ' no ' + fmtN(d.total) + ' ' +
            lvPlural(d.total, 'kopīga balsojuma', 'kopīgiem balsojumiem') + '.</p>' +
          '<p class="link-desc" style="color:var(--text-muted);">' + escHtml(rankLabel) + ' (' + escHtml(sourceName) + ' sarakstā).</p>' +
        '</div>';
    } else {
      // Find the matching tension to get source_url + target_url
      var matchTension = tensionsData.find(function(t) {
        return t.topic === d.topic && t.tension_type === d.tension_type &&
          t.source_name === sourceName && t.target_name === targetName;
      });
      var tUrl = matchTension ? matchTension.source_url : '';
      var tUrl2 = matchTension ? matchTension.target_url : '';
      html += '<p class="detail-section-title">Saite</p>' +
        '<div class="detail-link-card" style="border-color:' +
          (d.tension_type === 'uzbrukums' ? 'var(--red-bright)' : d.tension_type === 'atbalsts' ? 'var(--green)' : d.tension_type === 'politikas nostāju konflikts' ? 'var(--accent)' : 'var(--yellow)') +
          ';">' +
          '<div class="panel-tension-header">' +
            '<span class="badge ' + badgeClass(d.tension_type) + '">' + escHtml(typeLabel(d.tension_type)) + '</span>' +
            '<span class="topic-tag">' + escHtml(d.topic) + '</span>' +
          '</div>' +
          '<div class="link-parties" style="font-size:1rem;margin:0.75rem 0;">' +
            '<a href="politiki/' + escHtml(sourceSlug) + '.html" style="color:var(--accent);">' + escHtml(sourceName) + '</a>' +
            '<span class="link-arrow" style="font-size:1.2rem;">&rarr;</span>' +
            '<a href="politiki/' + escHtml(targetSlug) + '.html" style="color:var(--accent);">' + escHtml(targetName) + '</a>' +
          '</div>' +
          '<div class="link-desc" style="margin:0.5rem 0;">' + escHtml(d.label || '') + '</div>' +
          '<div class="link-footer">' +
            '<div>' + sourceLink(tUrl, sourceSlug, sourceName) +
              (tUrl2 ? ' &middot; ' + sourceLink(tUrl2, targetSlug, targetName) : '') +
            '</div>' +
          '</div>' +
        '</div>';
    }

    // Find other tensions between these two
    var others = tensionsData.filter(function(t) {
      return (t.source_name === sourceName && t.target_name === targetName) ||
             (t.source_name === targetName && t.target_name === sourceName);
    });
    // Exclude the one we just showed (by matching topic+type)
    var extra = others.filter(function(t) {
      return !(t.topic === d.topic && t.tension_type === d.tension_type);
    });

    if (extra.length > 0) {
      html += '<hr class="detail-divider"><p class="detail-section-title">Citas saites starp šiem politiķiem</p>';
      extra.forEach(function(t) {
        html += '<div class="detail-link-card">' +
          '<div class="panel-tension-header">' +
            '<span class="badge ' + badgeClass(t.tension_type) + '">' + escHtml(typeLabel(t.tension_type)) + '</span>' +
            '<span class="topic-tag">' + escHtml(t.topic) + '</span>' +
          '</div>' +
          '<div class="link-desc">' + escHtml(t.description || '') + '</div>' +
          '<div class="link-footer">' +
            '<div>' + sourceLink(t.source_url, t.source_slug, t.source_name) +
              (t.target_url ? ' &middot; ' + sourceLink(t.target_url, t.target_slug, t.target_name) : '') +
            '</div>' +
          '</div>' +
        '</div>';
      });
    }

    detailContent.innerHTML = html;
  };
}
