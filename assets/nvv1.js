/* nvv1.js — NVO dotāciju analīzes lapa (analizes/nvo-dotacijas-2025.html).
   Dati nāk no ne-izpildāmā <script type="application/json" id="nvo-data"> bloka
   (CSP: script-src bez 'unsafe-inline' — tāpēc viss izpildāmais dzīvo šeit). */
(function () {
  var dataEl = document.getElementById('nvo-data');
  if (!dataEl) return;
  var raw = JSON.parse(dataEl.textContent);
  // rows: [name, dot, ien, region]
  var data = raw.map(function (r) {
    return { name: r[0], dot: r[1], ien: r[2], reg: r[3] || '', dep: r[2] > 0 ? r[1] / r[2] : 0 };
  });

  function fold(s) {
    return s.toLowerCase()
      .replace(/ā/g, 'a').replace(/č/g, 'c').replace(/ē/g, 'e').replace(/ģ/g, 'g')
      .replace(/ī/g, 'i').replace(/ķ/g, 'k').replace(/ļ/g, 'l').replace(/ņ/g, 'n')
      .replace(/š/g, 's').replace(/ū/g, 'u').replace(/ž/g, 'z');
  }
  data.forEach(function (d) { d.hay = fold(d.name + ' ' + d.reg); });

  function eur(n) {
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace('.', ',') + ' M€';
    if (n >= 1e3) return Math.round(n / 1e3) + ' t€';
    return n + ' €';
  }
  function eurFull(n) { return n.toLocaleString('lv-LV') + ' €'; }

  /* ---------- table ---------- */
  var tbody = document.getElementById('tbody');
  var tcount = document.getElementById('tcount');
  var q = document.getElementById('q');
  var sortsel = document.getElementById('sortsel');
  var LIMIT = 20;

  function depColor(dep) {
    if (dep >= 0.95) return 'var(--hl)';
    if (dep >= 0.75) return 'var(--orange)';
    if (dep < 0.25) return 'var(--green)';
    return 'var(--accent)';
  }

  function renderTable() {
    var needle = fold(q.value.trim());
    var rows = needle
      ? data.filter(function (d) { return d.hay.indexOf(needle) !== -1; })
      : data.slice();
    var mode = sortsel.value;
    rows.sort(function (a, b) {
      if (mode === 'dep') return b.dep - a.dep || b.dot - a.dot;
      if (mode === 'ien') return b.ien - a.ien;
      if (mode === 'min') return a.dot - b.dot;
      return b.dot - a.dot;
    });
    var shown = rows.slice(0, LIMIT);
    var html = shown.map(function (d) {
      var pct = Math.round(d.dep * 100);
      return '<tr><td class="org">' + escapeHtml(d.name) +
        (d.reg ? '<span class="sub2">' + escapeHtml(d.reg) + '</span>' : '') +
        '</td><td class="num" title="' + eurFull(d.dot) + '">' + eur(d.dot) +
        '</td><td class="num" title="' + eurFull(d.ien) + '">' + eur(d.ien) +
        '</td><td><span class="depb"><i style="width:' + pct + '%;background:' + depColor(d.dep) + '"></i></span>' +
        '<span class="num">' + pct + '%</span></td></tr>';
    }).join('');
    tbody.innerHTML = html || '<tr><td colspan="4" style="color:var(--text-dim)">Nekas netika atrasts.</td></tr>';
    tcount.textContent = rows.length === data.length
      ? 'Rāda ' + shown.length + ' no ' + data.length + ' organizācijām.'
      : 'Atrastas ' + rows.length + ' organizācijas' + (rows.length > LIMIT ? ', rāda pirmās ' + LIMIT + '.' : '.');
  }
  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  q.addEventListener('input', renderTable);
  sortsel.addEventListener('change', renderTable);
  renderTable();

  /* ---------- scatter ---------- */
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

  function showTip(e) {
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
      tip.innerHTML = '<b>' + escapeHtml(best.d.name) + '</b>' +
        (best.d.reg ? escapeHtml(best.d.reg) + '<br>' : '') +
        '<span class="tn">Dotācijas: ' + eurFull(best.d.dot) + '<br>Ieņēmumi: ' + eurFull(best.d.ien) +
        '<br>Atkarība: ' + Math.round(best.d.dep * 100) + '%</span>';
    } else {
      tip.style.display = 'none';
    }
  }
  canvas.addEventListener('pointermove', showTip);
  // Skārienekrānā hover nav — tas pats tuvākā punkta meklējums uz pieskārienu.
  canvas.addEventListener('pointerdown', showTip);
  canvas.addEventListener('pointerleave', function () { tip.style.display = 'none'; });

  var rT;
  window.addEventListener('resize', function () { clearTimeout(rT); rT = setTimeout(draw, 120); });
  new MutationObserver(draw).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', draw);
  }
  draw();
})();
