// nvv2.js — NVO 'Valsts maksājumi NVO' lapa (analizes/nvo-valsts-maksajumi.html)
// Avots: data/NVO/nvo-maksajumi-v2.html (ģenerēts no jaunaki_sources/_buve_lapu_v2.py).
// Ja lapa mainās: labot ģeneratorā, pārģenerēt, un atkārtot šo izvilkšanu
// (divi IIFE: 1) tabula/kartiņa/meklētājs + window.NVO, 2) aina scatter; secība obligāta).

(function () {
  var payload = JSON.parse(document.getElementById('nvo-data').textContent);
  var MINS = payload.mins;
  var MINS_FULL = payload.mins_full;
  // ieraksts: [reg, name, y24, y25, y26, mins[], ien, dotLpa, pilseta, joma, web, fb, ig, apraksts]
  var data = payload.org;

  function fold(s) {
    return s.toLowerCase()
      .replace(/ā/g,'a').replace(/č/g,'c').replace(/ē/g,'e').replace(/ģ/g,'g')
      .replace(/ī/g,'i').replace(/ķ/g,'k').replace(/ļ/g,'l').replace(/ņ/g,'n')
      .replace(/š/g,'s').replace(/ū/g,'u').replace(/ž/g,'z');
  }
  data.forEach(function (d) { d.hay = fold(d[1] + ' ' + d[0] + ' ' + (d[8] || '') + ' ' + (d[9] || '')); });

  function eur(n) {
    if (n == null) return '—';
    if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1).replace('.', ',') + ' M€';
    if (Math.abs(n) >= 1e3) return Math.round(n / 1e3) + ' t€';
    return Math.round(n) + ' €';
  }
  function eurFull(n) { return n == null ? '—' : n.toLocaleString('lv-LV') + ' €'; }
  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  var tbody = document.getElementById('tbody');
  var tcount = document.getElementById('tcount');
  var q = document.getElementById('q');
  var sortsel = document.getElementById('sortsel');
  var LIMIT = 20;
  var openIdx = -1;

  function cardHtml(d) {
    var h = '<div class="ocard"><div class="ocard-title">' + esc(d[1]) + ' <span class="sub2">reģ. nr. ' + esc(d[0]) + '</span></div>';
    var mx = Math.max(d[2], d[3], d[4], 1);
    var years = [[2024, d[2]], [2025, d[3]], ['2026*', d[4]]];
    h += '<div class="ybars">';
    years.forEach(function (yv) {
      var w = Math.max(1.5, yv[1] / mx * 100);
      h += '<div class="ybar"><span class="yl">' + yv[0] + '</span>' +
           '<span class="yt"><i style="width:' + w.toFixed(1) + '%"></i></span>' +
           '<span class="yv">' + eurFull(yv[1]) + '</span></div>';
    });
    h += '</div>';
    if (d[5] && d[5].length) {
      var nm = d[5].length;
      var iw = (nm % 10 === 1 && nm % 100 !== 11) ? ' valsts iestāde' : ' valsts iestādes';
      h += '<div class="oline">Naudu maksā ' + nm + iw + ': <b>' +
           d[5].map(function (i) { return esc(MINS_FULL[i]); }).join(', ') + '</b></div>';
    }
    if (d[6]) {
      var dep = Math.round(d[7] / d[6] * 100);
      h += '<div class="oline">2025. gada pārskatā: ieņēmumi ' + eurFull(d[6]) +
           ', no tiem dotācijas un subsīdijas (visi avoti, arī pašvaldības) ' + eurFull(d[7]) + '.</div>' +
           '<div class="oline"><b>Atkarība no dotācijām un subsīdijām: ' + dep + '%</b> no kopējiem ieņēmumiem.</div>';
    } else {
      h += '<div class="oline dim">Gada pārskata dati (ieņēmumi, atkarības %) šai organizācijai nav pieejami — tās nav LPA izvilkumā.</div>';
    }
    var meta2 = [];
    if (d[15]) meta2.push('Joma: ' + esc(d[15]));
    if (d[8]) meta2.push(esc(d[8]));
    if (meta2.length) h += '<div class="oline dim">' + meta2.join(' · ') + '</div>';
    if (d[13]) h += '<div class="oline">' + esc(d[13]) + '</div>';
    if (d[14]) h += '<div class="oline dim">⚠ ' + esc(d[14]) + '</div>';
    var links = [];
    if (d[10]) links.push('<a href="' + esc(d[10]) + '" target="_blank" rel="noopener">Mājaslapa ↗</a>');
    if (d[11]) links.push('<a href="' + esc(d[11]) + '" target="_blank" rel="noopener">Facebook ↗</a>');
    if (d[12]) links.push('<a href="' + esc(d[12]) + '" target="_blank" rel="noopener">Instagram ↗</a>');
    if (links.length) h += '<div class="olinks">' + links.join('') + '</div>';
    return h + '</div>';
  }

  function render() {
    var needle = fold(q.value.trim());
    var rows = needle
      ? data.filter(function (d) { return d.hay.indexOf(needle) !== -1; })
      : data.slice();
    var mode = sortsel.value;
    rows.sort(function (a, b) {
      if (mode === 'y26') return b[4] - a[4];
      if (mode === 'y24') return b[2] - a[2];
      if (mode === 'growth') return (b[3] - b[2]) - (a[3] - a[2]);
      if (mode === 'abc') return a[1].localeCompare(b[1], 'lv');
      return b[3] - a[3];
    });
    var shown = rows.slice(0, LIMIT);
    if (openIdx !== -1 && shown.indexOf(data[openIdx]) === -1) shown.unshift(data[openIdx]);
    var html = shown.map(function (d) {
      var i = data.indexOf(d);
      return '<tr data-i="' + i + '" class="clck' + (i === openIdx ? ' open' : '') + '">' +
        '<td class="org">' + esc(d[1]) + '<span class="sub2">' + esc(d[0]) + '</span></td>' +
        '<td class="num" title="' + eurFull(d[2]) + '">' + eur(d[2]) + '</td>' +
        '<td class="num" title="' + eurFull(d[3]) + '">' + eur(d[3]) + '</td>' +
        '<td class="num" title="' + eurFull(d[4]) + '">' + eur(d[4]) + '</td>' +
        '<td class="num">' + (d[5] ? d[5].length : 0) + '</td></tr>' +
        (i === openIdx ? '<tr class="cardrow"><td colspan="5">' + cardHtml(d) + '</td></tr>' : '');
    }).join('');
    tbody.innerHTML = html || '<tr><td colspan="5" style="color:var(--text-dim)">Nekas netika atrasts.</td></tr>';
    try {
      if (openIdx !== -1) history.replaceState(null, '', '#org=' + data[openIdx][0]);
      else if (location.hash.indexOf('#org=') === 0) history.replaceState(null, '', location.pathname);
    } catch (e) {}
    tcount.textContent = (rows.length === data.length
      ? 'Rāda ' + shown.length + ' no ' + data.length + ' organizācijām.'
      : 'Atrastas ' + rows.length + ' organizācijas' + (rows.length > LIMIT ? ', rāda pirmās ' + LIMIT + '.' : '.')) + ' * 2026. gads — līdz 15. jūlijam. Min. = no cik valsts iestādēm organizācija saņēma naudu.';
  }

  tbody.addEventListener('click', function (e) {
    var tr = e.target.closest('tr.clck');
    if (!tr) return;
    var i = parseInt(tr.getAttribute('data-i'), 10);
    openIdx = (openIdx === i) ? -1 : i;
    render();
    if (openIdx !== -1) {
      var card = tbody.querySelector('tr.cardrow');
      if (card) card.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  });
  q.addEventListener('input', function () { openIdx = -1; render(); });
  sortsel.addEventListener('change', function () { openIdx = -1; render(); });
  if (location.hash.indexOf('#org=') === 0) {
    var reg0 = location.hash.slice(5);
    var i0 = data.findIndex(function (d) { return d[0] === reg0; });
    if (i0 >= 0) openIdx = i0;
  }
  render();

  /* aina grafika punkta klikšķis -> atver org. kartiņu šeit */
  var nameIdx = null;
  window.NVO = {
    findByName: function (rawName) {
      if (!nameIdx) {
        nameIdx = {};
        data.forEach(function (d, i) {
          nameIdx[fold(d[1])] = i;
          var stripped = fold(d[1].replace(/["„“”]/g, '').replace(/^(biedrība|nodibinājums|fonds)\s+/i, ''));
          if (!(stripped in nameIdx)) nameIdx[stripped] = i;
        });
      }
      var k = fold(rawName);
      if (k in nameIdx) return nameIdx[k];
      k = k.replace(/["„“”]/g, '').replace(/^(biedrība|nodibinājums|fonds)\s+/i, '');
      return (k in nameIdx) ? nameIdx[k] : -1;
    },
    open: function (i) {
      q.value = '';
      openIdx = i;
      render();
      var card = tbody.querySelector('tr.cardrow');
      if (card) card.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  };

  /* ---------- jomu izklāji + politisko saraksts ---------- */
  function openOrgByIdx(i) { window.NVO.open(i); }
  var jomarows = document.getElementById('jomarows');
  function toggleJoma(row) {
    var next = row.nextElementSibling;
    if (next && next.classList.contains('geolist')) { next.remove(); row.classList.remove('open'); return; }
    var cat = row.getAttribute('data-cat');
    var idxs = [];
    data.forEach(function (d, i) { if (d[15] === cat && d[3] > 0) idxs.push(i); });
    idxs.sort(function (a, b) { return data[b][3] - data[a][3]; });
    var cap = idxs.slice(0, 200);
    var div = document.createElement('div');
    div.className = 'geolist';
    div.innerHTML = cap.map(function (i) {
      var d = data[i];
      return '<div class="gitem" data-i="' + i + '"><span class="gname">' + esc(d[1]) +
             '</span><span class="gsum">' + eur(d[3]) + '</span></div>';
    }).join('') + (idxs.length > 200
      ? '<div class="gitem dim">…rāda 200 lielākās no ' + idxs.length + ' — pārējās atrodamas meklētājā.</div>' : '');
    row.parentNode.insertBefore(div, row.nextSibling);
    row.classList.add('open');
  }
  if (jomarows) {
    jomarows.addEventListener('click', function (e) {
      var item = e.target.closest('.gitem[data-i]');
      if (item) { openOrgByIdx(parseInt(item.getAttribute('data-i'), 10)); return; }
      var row = e.target.closest('.jomarow');
      if (row) toggleJoma(row);
    });
    jomarows.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      var row = e.target.closest('.jomarow');
      if (row) { e.preventDefault(); toggleJoma(row); }
    });
  }
  var pollist = document.getElementById('pollist');
  if (pollist) {
    pollist.addEventListener('click', function (e) {
      var item = e.target.closest('.gitem[data-name]');
      if (!item) return;
      var idx = window.NVO.findByName(item.getAttribute('data-name'));
      if (idx >= 0) openOrgByIdx(idx);
    });
  }
  var noweb = document.getElementById('noweb');
  if (noweb) {
    noweb.addEventListener('click', function (e) {
      var item = e.target.closest('.nwitem[data-name]');
      if (!item) return;
      var idx = window.NVO.findByName(item.getAttribute('data-name'));
      if (idx >= 0) openOrgByIdx(idx);
    });
  }
})();

(function () {
  var raw = JSON.parse(document.getElementById('nvo-lpa').textContent);
  var data = raw.map(function (r) {
    return { name: r[0], dot: r[1], ien: r[2], reg: r[3] || '', dep: r[2] > 0 ? r[1] / r[2] : 0 };
  });
  function eurFull(n) { return n.toLocaleString('lv-LV') + ' €'; }
  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  var canvas = document.getElementById('sc');
  var tip = document.getElementById('tip');
  var ctx = canvas.getContext('2d');
  var pts = [];
  var PAD = { l: 46, r: 14, t: 14, b: 30 };
  var XMIN = Math.log10(50), XMAX = Math.log10(4.5e7);
  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }
  function draw() {
    var w = canvas.clientWidth, h = canvas.clientHeight;
    var dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr; canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    var cGrid = cssVar('--border-soft'), cText = cssVar('--text-dim');
    var cAccent = cssVar('--accent'), cHot = cssVar('--hl'), cGreen = cssVar('--green'), cOrange = cssVar('--orange');
    var iw = w - PAD.l - PAD.r, ih = h - PAD.t - PAD.b;
    function X(ien) { return PAD.l + (Math.log10(Math.max(ien, 50)) - XMIN) / (XMAX - XMIN) * iw; }
    function Y(dep) { return PAD.t + (1 - dep) * ih; }
    ctx.font = '10px sans-serif';
    ctx.fillStyle = cText; ctx.strokeStyle = cGrid; ctx.lineWidth = 1;
    [0, .25, .5, .75, 1].forEach(function (v) {
      var y = Y(v);
      ctx.beginPath(); ctx.moveTo(PAD.l, y); ctx.lineTo(w - PAD.r, y); ctx.stroke();
      ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
      ctx.fillText(Math.round(v * 100) + '%', PAD.l - 6, y);
    });
    [100, 1e3, 1e4, 1e5, 1e6, 1e7].forEach(function (v) {
      var x = X(v);
      ctx.beginPath(); ctx.moveTo(x, PAD.t); ctx.lineTo(x, h - PAD.b); ctx.stroke();
      ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      var lbl = v >= 1e6 ? (v / 1e6) + ' M€' : v >= 1e3 ? (v / 1e3) + ' t€' : v + ' €';
      ctx.fillText(lbl, x, h - PAD.b + 6);
    });
    pts = [];
    data.forEach(function (d) {
      var x = X(d.ien), y = Y(Math.min(d.dep, 1));
      var r = Math.max(1.6, Math.sqrt(d.dot) / 320);
      var col = d.dep >= 0.95 ? cHot : d.dep >= 0.75 ? cOrange : d.dep < 0.25 ? cGreen : cAccent;
      ctx.globalAlpha = 0.62;
      ctx.fillStyle = col;
      ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
      pts.push({ x: x, y: y, r: r, d: d });
    });
    ctx.globalAlpha = 1;
  }
  function pick(e) {
    var rect = canvas.getBoundingClientRect();
    var mx = e.clientX - rect.left, my = e.clientY - rect.top;
    var best = null, bd = 144;
    for (var i = 0; i < pts.length; i++) {
      var p = pts[i];
      var dx = p.x - mx, dy = p.y - my;
      var dist = dx * dx + dy * dy - p.r * p.r;
      if (dist < bd) { bd = dist; best = p; }
    }
    if (best) {
      tip.style.display = 'block';
      var left = Math.min(mx + 14, rect.width - 270);
      tip.style.left = Math.max(0, left) + 'px';
      tip.style.top = (my + 16) + 'px';
      tip.innerHTML = '<b>' + esc(best.d.name) + '</b>' +
        (best.d.reg ? esc(best.d.reg) + '<br>' : '') +
        '<span class="tn">Dotācijas: ' + eurFull(best.d.dot) + '<br>Ieņēmumi: ' + eurFull(best.d.ien) +
        '<br>Atkarība: ' + Math.round(best.d.dep * 100) + '%</span>';
    } else {
      tip.style.display = 'none';
      sticky = false;
    }
  }
  var sticky = false;
  canvas.addEventListener('pointermove', function (e) { if (!sticky) pick(e); });
  canvas.addEventListener('pointerdown', function (e) {
    if (e.pointerType === 'touch') sticky = true;
    pick(e);
    if (tip.style.display !== 'none' && window.NVO) {
      var nameEl = tip.querySelector('b');
      if (nameEl) {
        var idx = window.NVO.findByName(nameEl.textContent);
        if (idx >= 0) { window.NVO.open(idx); sticky = false; tip.style.display = 'none'; }
      }
    }
  });
  canvas.addEventListener('pointerleave', function () { if (!sticky) tip.style.display = 'none'; });
  var rT;
  window.addEventListener('resize', function () { clearTimeout(rT); rT = setTimeout(draw, 120); });
  new MutationObserver(draw).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', draw);
  }
  draw();

  /* ---------- ģeogrāfijas reģionu izklāji ---------- */
  function foldR(s) {
    return s.toLowerCase().replace(/ā/g,'a').replace(/č/g,'c').replace(/ē/g,'e').replace(/ģ/g,'g')
      .replace(/ī/g,'i').replace(/ķ/g,'k').replace(/ļ/g,'l').replace(/ņ/g,'n')
      .replace(/š/g,'s').replace(/ū/g,'u').replace(/ž/g,'z').replace(/novads/g, 'nov.');
  }
  var byRegion = {};
  data.forEach(function (d) {
    var k = foldR(d.reg || 'citur');
    (byRegion[k] = byRegion[k] || []).push(d);
  });
  Object.keys(byRegion).forEach(function (k) {
    byRegion[k].sort(function (a, b) { return b.dot - a.dot; });
  });
  var georows = document.getElementById('georows');
  function eurR(n) {
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace('.', ',') + ' M€';
    if (n >= 1e3) return Math.round(n / 1e3) + ' t€';
    return n + ' €';
  }
  function toggleRegion(row) {
    var next = row.nextElementSibling;
    if (next && next.classList.contains('geolist')) {
      next.remove();
      row.classList.remove('open');
      return;
    }
    var key = foldR(row.getAttribute('data-region') || '');
    var orgs = byRegion[key] || [];
    var div = document.createElement('div');
    div.className = 'geolist';
    div.innerHTML = orgs.map(function (d) {
      return '<div class="gitem" data-name="' + esc(d.name) + '">' +
        '<span class="gname">' + esc(d.name) + '</span>' +
        '<span class="gsum">' + eurR(d.dot) + '</span></div>';
    }).join('') || '<div class="gitem dim">Nav datu.</div>';
    row.parentNode.insertBefore(div, row.nextSibling);
    row.classList.add('open');
  }
  if (georows) {
    georows.addEventListener('click', function (e) {
      var item = e.target.closest('.gitem[data-name]');
      if (item) {
        var gi = item.closest('.geolist');
        if (gi) e.stopPropagation();
        if (window.NVO) {
          var idx = window.NVO.findByName(item.getAttribute('data-name'));
          if (idx >= 0) window.NVO.open(idx);
        }
        return;
      }
      var row = e.target.closest('.georow');
      if (row) toggleRegion(row);
    });
    georows.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      var row = e.target.closest('.georow');
      if (row) { e.preventDefault(); toggleRegion(row); }
    });
  }
})();
