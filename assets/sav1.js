// sav1.js — saites lapas (politiķu savstarpējo saišu grafs) klienta puses skripts.
//   1) D3 spēka grafs (mezgli = politiķi, līnijas = spriedzes/balsojumi/kopīgās tēmas),
//   2) tabulas filtri (tips + partija + persona) ar URL sinhronizāciju,
//   3) detaļu panelis (mezgla/līnijas klikšķis → pozīcijas/saites/balsojumi/pretrunas).
//
// Lapas dati nāk no viena <script type="application/json" id="saites-data"> bloka:
//   { graph, tensions, contrasByPid, partyColors }.
// D3 ielādēts sinhroni no d3js.org PIRMS šī faila (bez defer), tāpēc d3 ir pieejams šeit.
//
// claims + mazā {pid: vote_count} karte lēni ielādējas no data/saites-data.json
// pirmajā detaļu atvēršanā. Smagais balsojumu reģistrs (votesMeta/votesByPid) dzīvo
// data/saites-votes.json un ielādējas tikai tad, kad atver "Balsojumi" sekciju —
// tā izplatītais detaļu-atvēršanas fetch paliek ~6× vieglāks. Sk. _emit_saites_json.

// ── Lapas dati no JSON bloka ──
var _saitesDataEl = document.getElementById('saites-data');
var _saitesJson = _saitesDataEl ? JSON.parse(_saitesDataEl.textContent) : {};
const graphData = _saitesJson.graph || { nodes: [], links: [] };
const tensionsData = _saitesJson.tensions || [];
const contrasByPid = _saitesJson.contrasByPid || {};
const _partyColorsData = _saitesJson.partyColors || {};

// Lēni ielādētās kešatmiņas (kods, ne dati — sākotnēji tukši, aizpildās ar fetch).
let claimsByPid = {};
let votesCount = {};
let votesMeta = [];
let votesByPid = {};
let _saitesDataLoaded = false;
let _saitesDataPromise = null;
let _saitesVotesLoaded = false;
let _saitesVotesPromise = null;

(function() {
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
    window.addEventListener('resize', function() {
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

    // Party colors — single source of truth: src/render/_common.py PARTY_COLORS
    // (emitted server-side via the #saites-data block). Unmapped parties fall back
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
    var activeFilters = new Set(['uzbrukums', 'spriedze', 'atbalsts', 'vote', 'shared_topic']);
    // Expose so URL-init can sync graph with table type filter
    window._graphActiveFilters = activeFilters;

    // Link stroke width
    function linkWidth(d) {
      if (d.type === 'tension') return 2.5;
      if (d.type === 'support') return 2;
      if (d.type === 'vote') return Math.max(0.8, Math.min((d.agree_pct || 50) / 30, 2.5));
      return Math.max(0.5, Math.min((d.weight || 1) * 0.4, 2));
    }

    // Link color
    function linkColor(d) {
      if (d.type === 'tension') {
        if (d.tension_type === 'spriedze') return cssVar('--yellow');
        return cssVar('--red-bright');  // uzbrukums
      }
      if (d.type === 'support') return cssVar('--green');
      if (d.type === 'vote') {
        var pct = d.agree_pct || 50;
        // Red (disagree) → purple (neutral) → purple (agree)
        if (pct >= 70) return cssVar('--purple') + '80';
        if (pct <= 30) return cssVar('--red-bright') + '4D';
        return cssVar('--purple') + '40';
      }
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
      .style('cursor', function(d) { return (d.type === 'tension' || d.type === 'support' || d.type === 'vote' || d.type === 'shared_topic') ? 'pointer' : 'default'; });
    // Visible line
    linkGroup.append('line')
      .attr('stroke', linkColor)
      .attr('stroke-width', linkWidth)
      .attr('stroke-dasharray', function(d) {
        if (d.type === 'vote') return '3,2';
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
    window._applyGraphLinkFilters = applyLinkFilters;
    applyLinkFilters();

    // Filter button click handlers
    document.querySelectorAll('.link-filter-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var type = btn.dataset.linkType;
        if (activeFilters.has(type)) {
          activeFilters.delete(type);
          btn.classList.remove('active');
        } else {
          activeFilters.add(type);
          btn.classList.add('active');
        }
        applyLinkFilters();
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

    // Selected state tracking
    var selectedNodeId = null;

    // Hover: highlight connected nodes (no tooltip — detail goes to panel)
    node.on('mouseover', function(event, d) {
      d3.select(this).select('circle').attr('stroke', cssVar('--graph-node-stroke-hover')).attr('stroke-width', 2.5);
      // Dim unconnected
      link.attr('opacity', function(l) {
        return (l.source.id === d.id || l.target.id === d.id) ? 1 : 0.08;
      });
      node.attr('opacity', function(n) {
        if (n.id === d.id) return 1;
        return simLinks.some(function(l) {
          return (l.source.id === d.id && l.target.id === n.id) ||
                 (l.target.id === d.id && l.source.id === n.id);
        }) ? 1 : 0.15;
      });
    })
    .on('mouseout', function(event, d) {
      d3.select(this).select('circle')
        .attr('stroke', selectedNodeId === d.id ? 'var(--accent)' : cssVar('--graph-node-stroke'))
        .attr('stroke-width', selectedNodeId === d.id ? 3 : 1.5);
      link.attr('opacity', 1);
      node.attr('opacity', 1);
    })
    .on('click', function(event, d) {
      event.stopPropagation();
      selectedNodeId = d.id;
      // Highlight selected node
      node.select('circle')
        .attr('stroke', function(n) { return n.id === d.id ? 'var(--accent)' : cssVar('--graph-node-stroke'); })
        .attr('stroke-width', function(n) { return n.id === d.id ? 3 : 1.5; });
      showNodeDetail(d);
    });

    // Link interactions — click to show detail in panel
    link.on('mouseover', function(event, d) {
      if (d.type === 'tension' || d.type === 'support' || d.type === 'vote' || d.type === 'shared_topic') {
        d3.select(this).select('line:nth-child(2)').attr('stroke-width', Math.max(linkWidth(d) * 2.5, 4));
      }
    })
    .on('mouseout', function(event, d) {
      d3.select(this).select('line:nth-child(2)').attr('stroke-width', linkWidth(d));
    })
    .on('click', function(event, d) {
      if (d.type !== 'tension' && d.type !== 'support' && d.type !== 'vote' && d.type !== 'shared_topic') return;
      event.stopPropagation();
      selectedNodeId = null;
      node.select('circle')
        .attr('stroke', cssVar('--graph-node-stroke'))
        .attr('stroke-width', 1.5);
      showLinkDetail(d);
    });

    // Click empty space to deselect
    svg.on('click', function() {
      selectedNodeId = null;
      node.select('circle')
        .attr('stroke', cssVar('--graph-node-stroke'))
        .attr('stroke-width', 1.5);
      showEmptyDetail();
    });

    // Simulation tick
    simulation.on('tick', function() {
      link.selectAll('line')
        .attr('x1', function(d) { return d.source.x; })
        .attr('y1', function(d) { return d.source.y; })
        .attr('x2', function(d) { return d.target.x; })
        .attr('y2', function(d) { return d.target.y; });
      node.attr('transform', function(d) { return 'translate(' + d.x + ',' + d.y + ')'; });
    });

    // Re-read tokens on theme switch — the persistent graph bakes resolved
    // colors into SVG attributes, so re-apply the styling pass (positions kept).
    if (_themeRestyle) document.removeEventListener('atmina:themechange', _themeRestyle);
    _themeRestyle = function() {
      link.select('line:nth-child(2)').attr('stroke', linkColor);
      node.select('circle')
        .attr('fill', function(d) { return partyColors[d.party] || cssVar('--text-muted'); })
        .attr('stroke', function(d) { return selectedNodeId === d.id ? 'var(--accent)' : cssVar('--graph-node-stroke'); })
        .style('filter', 'drop-shadow(0 0 3px ' + cssVar('--shadow-overlay') + ')');
      node.selectAll('text.node-surname').attr('fill', cssVar('--graph-label'));
    };
    document.addEventListener('atmina:themechange', _themeRestyle);
  }

  // ── Table filters: type + party + person, with URL sync ──
  const tableRows = document.querySelectorAll('#saites-table tbody tr');
  const selectedTableTypes = new Set();
  const selectedParties = new Set();
  const selectedPersons = new Set();

  function applyTableFilters() {
    tableRows.forEach(row => {
      const matchType = selectedTableTypes.size === 0 || selectedTableTypes.has(row.dataset.tensionType);
      const matchParty = selectedParties.size === 0 ||
        selectedParties.has(row.dataset.sourceParty) ||
        selectedParties.has(row.dataset.targetParty);
      const matchPerson = selectedPersons.size === 0 ||
        selectedPersons.has(row.dataset.sourceName) ||
        selectedPersons.has(row.dataset.targetName);
      row.style.display = (matchType && matchParty && matchPerson) ? '' : 'none';
    });
    syncGraphWithTableTypes();
    syncUrl();
  }

  function setupMultiSelect(selectId, triggerId, selectedSet, allLabel, pluralLabel, onChange) {
    const select = document.getElementById(selectId);
    const trigger = document.getElementById(triggerId);
    const label = trigger.querySelector('span');

    trigger.addEventListener('click', e => {
      e.stopPropagation();
      document.querySelectorAll('.multi-select.open').forEach(s => {
        if (s.id !== selectId) s.classList.remove('open');
      });
      select.classList.toggle('open');
      const search = select.querySelector('.multi-select-search');
      if (search && select.classList.contains('open')) setTimeout(() => search.focus(), 50);
    });

    select.querySelectorAll('.multi-select-option').forEach(opt => {
      opt.addEventListener('click', e => {
        e.stopPropagation();
        const val = opt.dataset.value;
        if (selectedSet.has(val)) { selectedSet.delete(val); opt.classList.remove('selected'); }
        else { selectedSet.add(val); opt.classList.add('selected'); }
        updateLabel();
        onChange();
      });
    });

    select.querySelector('.multi-select-clear').addEventListener('click', e => {
      e.stopPropagation();
      selectedSet.clear();
      select.querySelectorAll('.multi-select-option').forEach(o => o.classList.remove('selected'));
      updateLabel();
      onChange();
    });

    function updateLabel() {
      if (selectedSet.size === 0) { label.textContent = allLabel; trigger.classList.remove('has-selection'); }
      else if (selectedSet.size <= 2) { label.textContent = [...selectedSet].join(', '); trigger.classList.add('has-selection'); }
      else { label.textContent = selectedSet.size + ' ' + pluralLabel; trigger.classList.add('has-selection'); }
    }
    select._updateLabel = updateLabel;
  }

  setupMultiSelect('table-type-select', 'table-type-trigger', selectedTableTypes, 'Visi tipi', 'tipi', applyTableFilters);
  setupMultiSelect('party-select', 'party-trigger', selectedParties, 'Visas partijas', 'partijas', applyTableFilters);
  setupMultiSelect('person-select', 'person-trigger', selectedPersons, 'Visas personas', 'personas', applyTableFilters);

  document.addEventListener('click', e => {
    document.querySelectorAll('.multi-select.open').forEach(s => {
      if (!s.contains(e.target)) s.classList.remove('open');
    });
  });

  // Sync graph's tension-type filter buttons with table's type selection.
  // When no types selected → all tension types visible. When ≥1 selected → only those.
  // vote + shared_topic are left untouched (they're not tension types).
  function syncGraphWithTableTypes() {
    if (!window._graphActiveFilters || !window._applyGraphLinkFilters) return;
    const tensionTypes = ['uzbrukums', 'spriedze', 'atbalsts'];
    const allOn = selectedTableTypes.size === 0;
    tensionTypes.forEach(t => {
      if (allOn || selectedTableTypes.has(t)) window._graphActiveFilters.add(t);
      else window._graphActiveFilters.delete(t);
    });
    document.querySelectorAll('.link-filter-btn').forEach(btn => {
      const t = btn.dataset.linkType;
      if (tensionTypes.includes(t)) {
        btn.classList.toggle('active', allOn || selectedTableTypes.has(t));
      }
    });
    window._applyGraphLinkFilters();
  }

  // URL query-param sync: ?type=uzbrukums&party=ZZS&person=Andris+Kulbergs
  function syncUrl() {
    const params = new URLSearchParams();
    if (selectedTableTypes.size > 0) params.set('type', [...selectedTableTypes].join(','));
    if (selectedParties.size > 0) params.set('party', [...selectedParties].join(','));
    if (selectedPersons.size > 0) params.set('person', [...selectedPersons].join(','));
    const qs = params.toString();
    history.replaceState(null, '', window.location.pathname + (qs ? '?' + qs : ''));
  }

  function applyFromUrl() {
    const params = new URLSearchParams(window.location.search);
    function applyTo(paramName, selectId, set) {
      const val = params.get(paramName);
      if (!val) return;
      const wanted = new Set(val.split(',').map(v => v.trim()).filter(Boolean));
      const select = document.getElementById(selectId);
      select.querySelectorAll('.multi-select-option').forEach(opt => {
        if (wanted.has(opt.dataset.value)) {
          set.add(opt.dataset.value);
          opt.classList.add('selected');
        }
      });
      if (set.size > 0 && select._updateLabel) select._updateLabel();
    }
    applyTo('type', 'table-type-select', selectedTableTypes);
    applyTo('party', 'party-select', selectedParties);
    applyTo('person', 'person-select', selectedPersons);

    if (selectedTableTypes.size || selectedParties.size || selectedPersons.size) {
      applyTableFilters();
    }
  }

  applyFromUrl();

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

  function badgeClass(type) {
    if (type === 'uzbrukums') return 'badge-red';
    if (type === 'spriedze') return 'badge-yellow';
    if (type === 'atbalsts') return 'badge-green';
    return '';
  }

  function typeLabel(type) {
    if (type === 'uzbrukums') return 'Uzbrukums';
    if (type === 'spriedze') return 'Spriedze';
    if (type === 'atbalsts') return 'Atbalsts';
    return type || '';
  }

  // Generate source link — external URL or fallback to our site
  function sourceLink(url, fallbackSlug, fallbackLabel) {
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

  window.showEmptyDetail = function() {
    detailEmpty.style.display = '';
    detailContent.style.display = 'none';
  };

  var currentDetailNode = null;

  window.renderNodeSection = function(section) {
    if (!currentDetailNode) return;
    var d = currentDetailNode;
    var container = document.getElementById('detail-section-content');
    if (!container) return;

    // Update active tab
    document.querySelectorAll('.detail-stat-btn').forEach(function(btn) {
      btn.classList.toggle('active', btn.dataset.section === section);
    });

    if (section === 'pozicijas') {
      var claims = claimsByPid[d.id] || claimsByPid[String(d.id)] || [];
      if (claims.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);">Nav pozīciju.</p>';
        return;
      }
      var html = '';
      claims.forEach(function(c) {
        html += '<div class="detail-link-card">' +
          '<div class="panel-tension-header">' +
            '<span class="topic-tag">' + escHtml(c.topic) + '</span>' +
            '<span style="color:var(--text-muted);font-size:0.7rem;margin-left:auto;white-space:nowrap;">' + escHtml((c.date||'').substring(5)) + '</span>' +
          '</div>' +
          '<div class="link-desc">' + escHtml(c.stance) + '</div>' +
          '<div class="link-footer">' +
            sourceLink(c.source_url, d.slug, d.name) +
            '<span style="color:var(--text-muted);font-size:0.75rem;">tic. ' + (c.confidence || 0).toFixed(1) + '</span>' +
          '</div>' +
        '</div>';
      });
      container.innerHTML = html;

    } else if (section === 'saites') {
      var matching = tensionsData.filter(function(t) {
        return t.source_name === d.name || t.target_name === d.name;
      });
      if (matching.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);">Nav saišu.</p>';
        return;
      }
      var html = '';
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
            (t.date ? '<span style="color:var(--text-muted);font-size:0.8rem;">' + escHtml(t.date) + '</span>' : '') +
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
            '<span style="color:var(--text-muted);font-size:0.7rem;margin-left:auto;white-space:nowrap;">' + escHtml((meta.date||'').substring(5)) + '</span>' +
          '</div>' +
          '<div class="link-desc">' + escHtml(meta.motif) + '</div>' +
          '<div class="link-footer">' +
            '<a href="balsojumi.html#vote-' + meta.id + '">Balsojums &rarr;</a>' +
            (meta.url ? '<a href="' + escHtml(meta.url) + '" target="_blank" rel="noopener" style="color:var(--text-muted);font-size:0.75rem;">Saeima &rarr;</a>' : '') +
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
                       c.severity === 'reversal' ? 'Apvērsums' : 'Nobīde';
        html += '<div class="detail-link-card" style="border-left:3px solid var(--red-bright);">' +
          '<div class="panel-tension-header">' +
            '<span class="badge ' + sevBadge + '">' + escHtml(sevLabel) + '</span>' +
            '<span class="topic-tag">' + escHtml(c.topic) + '</span>' +
            '<span style="color:var(--text-muted);font-size:0.7rem;margin-left:auto;white-space:nowrap;">' + escHtml((c.date||'').substring(5)) + '</span>' +
          '</div>' +
          '<div class="link-desc">' + escHtml(c.summary) + '</div>';
        if (c.old_stance || c.new_stance) {
          var oldLbl = c.old_label || 'Iepriekš';
          var newLbl = c.new_label || 'Pašlaik';
          html += '<div style="margin-top:0.4rem;font-size:0.8rem;">';
          if (c.old_stance) html += '<div style="color:var(--text-muted);margin-bottom:0.2rem;"><span style="opacity:0.5;">' + escHtml(oldLbl) + ':</span> ' + escHtml(c.old_stance) +
            (c.old_url ? ' <a href="' + escHtml(c.old_url) + '" target="_blank" rel="noopener" style="color:var(--accent);font-size:0.75rem;">avots</a>' : '') + '</div>';
          if (c.new_stance) html += '<div style="color:var(--text-muted);"><span style="opacity:0.5;">' + escHtml(newLbl) + ':</span> ' + escHtml(c.new_stance) +
            (c.new_url ? ' <a href="' + escHtml(c.new_url) + '" target="_blank" rel="noopener" style="color:var(--accent);font-size:0.75rem;">avots</a>' : '') + '</div>';
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
    detailEmpty.style.display = 'none';
    detailContent.style.display = '';
    detailContent.innerHTML = '<p style="color:var(--text-muted);padding:1rem;">Ielādē…</p>';
    loadSaitesData().then(retry).catch(function() {
      detailContent.innerHTML = '<p style="color:var(--text-muted);padding:1rem;">Neizdevās ielādēt datus. Pārlādējiet lapu.</p>';
    });
  }

  window.showNodeDetail = function(d) {
    if (!_saitesDataLoaded) { ensureSaitesData(function() { window.showNodeDetail(d); }); return; }
    currentDetailNode = d;
    detailEmpty.style.display = 'none';
    detailContent.style.display = '';

    var matching = tensionsData.filter(function(t) {
      return t.source_name === d.name || t.target_name === d.name;
    });
    var contras = contrasByPid[d.id] || contrasByPid[String(d.id)] || [];
    var voteN = votesCount[d.id] || votesCount[String(d.id)] || 0;

    var html = '<h3>' + escHtml(d.name) + '</h3>' +
      '<div class="detail-subtitle"><span class="party-tag">' + escHtml(d.party) + '</span>' +
        ' <a href="politiki/' + escHtml(d.slug) + '.html" style="color:var(--accent);font-size:0.8rem;margin-left:0.5rem;">Profils &rarr;</a>' +
      '</div>' +
      '<div class="detail-meta">' +
        '<button class="detail-stat-btn active" data-section="pozicijas"><strong>' + d.claims + '</strong> pozīcijas</button>' +
        '<button class="detail-stat-btn" data-section="saites"><strong>' + matching.length + '</strong> saites</button>' +
        (voteN > 0 ? '<button class="detail-stat-btn" data-section="balsojumi" style="border-color:var(--purple);"><strong style="color:var(--purple);">' + voteN + '</strong> balsojumi</button>' : '') +
        (contras.length > 0 ? '<button class="detail-stat-btn" data-section="pretrunas" style="border-color:var(--red-bright);"><strong style="color:var(--red-bright);">' + contras.length + '</strong> pretrunas</button>' : '') +
      '</div>' +
      '<div id="detail-section-content"></div>';

    detailContent.innerHTML = html;
    // Default to pozīcijas tab
    renderNodeSection('pozicijas');
  };

  window.showLinkDetail = function(d) {
    if (!_saitesDataLoaded) { ensureSaitesData(function() { window.showLinkDetail(d); }); return; }
    detailEmpty.style.display = 'none';
    detailContent.style.display = '';

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
              '<span style="color:var(--text-muted);font-size:0.75rem;">' + escHtml(c.date) + '</span>' +
            '</div>' +
          '</div>';
        });
        return out;
      }
      html += renderTopicClaims(srcId, sourceName, sourceSlug);
      html += renderTopicClaims(tgtId, targetName, targetSlug);
    } else if (d.type === 'vote') {
      // Vote alignment detail
      var pct = d.agree_pct || 0;
      var barColor = pct >= 70 ? 'var(--purple)' : pct <= 30 ? 'var(--red-bright)' : 'var(--yellow)';
      html += '<p class="detail-section-title">Balsojumu sakritība</p>' +
        '<div class="detail-link-card" style="border-color:var(--purple);">' +
          '<div class="link-parties" style="font-size:1rem;margin:0 0 0.75rem;">' +
            '<a href="politiki/' + escHtml(sourceSlug) + '.html" style="color:var(--accent);">' + escHtml(sourceName) + '</a>' +
            '<span class="link-arrow" style="font-size:1.2rem;">&harr;</span>' +
            '<a href="politiki/' + escHtml(targetSlug) + '.html" style="color:var(--accent);">' + escHtml(targetName) + '</a>' +
          '</div>' +
          '<div style="margin-bottom:0.5rem;">' +
            '<div style="display:flex;justify-content:space-between;font-size:0.85rem;margin-bottom:0.25rem;">' +
              '<span>Sakritība</span><strong style="color:' + barColor + ';">' + pct + '%</strong>' +
            '</div>' +
            '<div style="background:var(--surface2);border-radius:4px;height:8px;overflow:hidden;">' +
              '<div style="background:' + barColor + ';width:' + pct + '%;height:100%;border-radius:4px;transition:width 0.3s;"></div>' +
            '</div>' +
          '</div>' +
          '<div class="link-desc">' + escHtml(d.label || '') + '</div>' +
          '<div class="link-footer">' +
            '<a href="balsojumi.html" style="color:var(--accent);">Balsojumi &rarr;</a>' +
          '</div>' +
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
          (d.tension_type === 'uzbrukums' ? 'var(--red-bright)' : d.tension_type === 'atbalsts' ? 'var(--green)' : 'var(--yellow)') +
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
})();
