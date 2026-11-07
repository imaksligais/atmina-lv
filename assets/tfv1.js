/* Izpētes tāfele — interakcija. Dati tikai no DOM (servera HTML ir pilns bez JS). */
(() => {
  const root = document.querySelector('.tf');
  if (!root) return;
  const board = root.querySelector('#tf-board');
  const svg = board.querySelector('.tf-threads');
  const panel = root.querySelector('#tf-panel');
  const closeup = root.querySelector('.tf-closeup');
  const book = root.querySelector('.tf-book');
  const phone = matchMedia('(max-width: 900px)');
  let phoneView = 'board';
  let overviewOpen = false;
  let overviewFit = false;
  const NS = 'http://www.w3.org/2000/svg';
  const links = [...root.querySelectorAll('.tf-book .tf-ledger .tf-link')].map(li => ({
    id: li.dataset.link, from: li.dataset.from, to: li.dataset.to,
    tier: li.dataset.tier, kind: li.dataset.kind, li }));
  const pairs = new Map();
  for (const l of links) {
    const key = [l.from, l.to].sort().join('|');
    if (!pairs.has(key)) pairs.set(key, []);
    pairs.get(key).push(l);
  }
  for (const group of pairs.values()) group.forEach((l, index) => {
    l.bendOffset = index * 36;
  });
  const nodeOf = id => board.querySelector(`[data-entity="${CSS.escape(id)}"]`);
  const detailOf = id => root.querySelector(`.tf-book [data-entity-detail="${CSS.escape(id)}"]`);
  let state = { sel: null, all: false, tiers: new Set(['1', '2', '3']), kinds: null, person: '' };
  let lastFocus = null;

  function centre(el) {
    const b = board.getBoundingClientRect(), r = el.getBoundingClientRect();
    return [r.left - b.left + r.width / 2, r.top - b.top + r.height / 2];
  }
  function edgePoint(el, toward) {
    const b = board.getBoundingClientRect(), r = el.getBoundingClientRect();
    const [cx, cy] = centre(el), [tx, ty] = toward;
    const dx = tx - cx, dy = ty - cy;
    const sx = (r.width / 2) / Math.abs(dx || 1e-6), sy = (r.height / 2) / Math.abs(dy || 1e-6);
    const s = Math.min(sx, sy, 1);
    return [cx + dx * s, cy + dy * s];
  }
  function pathFor(l) {
    const a = nodeOf(l.from), z = nodeOf(l.to);
    if (!a || !z || !board.getBoundingClientRect().width) return null;
    const [x1, y1] = edgePoint(a, centre(z)), [x2, y2] = edgePoint(z, centre(a));
    const dx = x2 - x1, dy = y2 - y1, length = Math.hypot(dx, dy) || 1;
    const bend = l.bendOffset * (dx >= 0 ? 1 : -1);
    const mx = (x1 + x2) / 2 - dy / length * bend;
    const my = (y1 + y2) / 2 + Math.min(40, length * 0.08) + dx / length * bend;
    const p = document.createElementNS(NS, 'path');
    p.setAttribute('d', `M${x1.toFixed(1)},${y1.toFixed(1)} Q${mx.toFixed(1)},${my.toFixed(1)} ${x2.toFixed(1)},${y2.toFixed(1)}`);
    p.dataset.link = l.id; p.dataset.tier = l.tier;
    const title = document.createElementNS(NS, 'title');
    title.textContent = l.li.querySelector('.tf-what').textContent.trim();
    p.append(title);
    p.addEventListener('click', () => select({ type: 'l', id: l.id }));
    return p;
  }

  function visibleLinks() {
    const s = state.sel;
    if (s && s.type === 'e') return links.filter(l => l.from === s.id || l.to === s.id);
    if (s && s.type === 'l') return links.filter(l => l.id === s.id);
    if (s && s.type === 'g') {
      const g = root.querySelector(`.tf-guide[data-article="${CSS.escape(s.id)}"]`);
      const ids = new Set((g?.dataset.guideLinks || '').split(' '));
      return links.filter(l => ids.has(l.id));
    }
    if (state.all) return links.filter(l => state.tiers.has(l.tier)
      && (!state.kinds || state.kinds.has(l.kind))
      && (!state.person || l.from === state.person || l.to === state.person));
    return [];
  }

  function draw() {
    svg.replaceChildren();
    const vis = visibleLinks();
    const selected = state.sel && state.sel.type !== 'z';
    for (const l of vis) {
      const p = pathFor(l);
      if (!p) continue;
      if (selected) p.classList.add('is-on');
      svg.appendChild(p);
    }
    const on = new Set(vis.flatMap(l => [l.from, l.to]));
    if (state.sel?.type === 'e') on.add(state.sel.id);
    const zone = state.sel?.type === 'z' ? state.sel.id : null;
    board.querySelectorAll('[data-entity]').forEach(n => {
      const id = n.dataset.entity;
      const dim = zone ? n.dataset.zone !== zone : (state.sel || state.all) && !on.has(id);
      n.classList.toggle('is-dim', !!dim);
      n.classList.toggle('is-sel', state.sel?.type === 'e' && state.sel.id === id);
    });
    board.querySelectorAll('.tf-zone').forEach(z => z.classList.toggle('is-sel', z.dataset.zone === zone));
    const count = root.querySelector('.tf-count');
    if (state.all && !state.sel) {
      count.textContent = vis.length
        ? `Rādīti ${vis.length} no ${links.length} diegiem. Saite nav pārkāpums.`
        : `Rādīti 0 no ${links.length} diegiem — šim filtram saišu nav. Notīri kādu filtru.`;
    } else count.textContent = '';
  }

  function fillPanel() {
    const s = state.sel;
    panel.replaceChildren();
    if (!s) panel.append(Object.assign(document.createElement('p'), { className: 'tf-panel-hint', textContent: 'Izvēlies cilvēku, kartīti vai diegu.' }));
    if (s?.type === 'e') {
      const d = detailOf(s.id);
      if (d) panel.append(d.cloneNode(true));
      const ol = document.createElement('ol'); ol.className = 'tf-ledger tf-panel-links';
      visibleLinks().forEach(l => { const c = l.li.cloneNode(true); c.removeAttribute('id'); ol.append(c); });
      panel.append(ol);
    } else if (s?.type === 'l') {
      const l = links.find(x => x.id === s.id); const c = l.li.cloneNode(true); c.removeAttribute('id');
      const d = c.querySelector('details'); if (d) d.open = true;
      const ol = document.createElement('ol'); ol.className = 'tf-ledger tf-panel-links';
      ol.append(c); panel.append(ol);
    } else if (s?.type === 'z') {
      const z = board.querySelector(`.tf-zone[data-zone="${CSS.escape(s.id)}"]`);
      const h = document.createElement('h3'); h.textContent = z.querySelector('span').textContent.trim();
      const note = root.querySelector(`.tf-book [data-zone-note="${CSS.escape(s.id)}"]`);
      panel.append(h);
      // Virsrakstā zonas nosaukums jau ir — piezīmes treknais sākums to tikai atkārtotu.
      if (note) { const nc = note.cloneNode(true); nc.querySelector('b')?.remove(); panel.append(nc); }
      const ul = document.createElement('ul'); ul.className = 'tf-zone-list';
      board.querySelectorAll(`[data-entity][data-zone="${CSS.escape(s.id)}"]`).forEach(n => {
        const li = document.createElement('li'); const b = document.createElement('button');
        b.type = 'button'; b.dataset.entity = n.dataset.entity;
        const label = n.querySelector('.tf-card-label'); const name = n.querySelector('.tf-card-name');
        if (label) b.append(label.cloneNode(true));
        b.append(name ? name.cloneNode(true) : n.textContent.trim());
        b.addEventListener('click', () => select({ type: 'e', id: n.dataset.entity }));
        li.append(b); ul.append(li);
      });
      panel.append(ul);
    } else if (s?.type === 'g') {
      const g = root.querySelector(`.tf-guide[data-article="${CSS.escape(s.id)}"]`);
      const a = document.createElement('a'); a.href = `${s.id}.html`; a.textContent = `Lasīt rakstu: ${g.textContent}`;
      panel.append(a);
    }
    panel.querySelectorAll('[id]').forEach(n => n.removeAttribute('id'));
    panel.append(Object.assign(document.createElement('p'), {
      className: 'tf-notguilt', textContent: 'Saite nav pārkāpums.'
    }));
  }

  function valid(s) {
    if (!s) return null;
    if (s.type === 'e') return nodeOf(s.id) ? s : null;
    if (s.type === 'l') return links.some(l => l.id === s.id) ? s : null;
    if (s.type === 'z') return board.querySelector(`.tf-zone[data-zone="${CSS.escape(s.id)}"]`) ? s : null;
    if (s.type === 'g') return root.querySelector(`.tf-guide[data-article="${CSS.escape(s.id)}"]`) ? s : null;
    return null;
  }

  function cleanClone(element) {
    const clone = element.cloneNode(true);
    clone.removeAttribute('id');
    clone.querySelectorAll('[id]').forEach(n => n.removeAttribute('id'));
    return clone;
  }
  function entityName(id) {
    return detailOf(id).querySelector('h3').textContent;
  }
  function renderCloseup() {
    closeup.replaceChildren();
    if (!phone.matches) return;
    const label = document.createElement('label');
    label.className = 'tf-picker'; label.textContent = 'Izvēlies kartīti';
    const picker = document.createElement('select'); picker.dataset.pickEntity = '';
    picker.append(new Option('Cilvēks vai uzņēmums', ''));
    board.querySelectorAll('[data-entity]').forEach(n => {
      picker.append(new Option(entityName(n.dataset.entity), n.dataset.entity));
    });
    picker.value = state.sel?.type === 'e' ? state.sel.id : '';
    label.append(picker); closeup.append(label);
    if (state.sel?.type === 'e') {
      const focus = cleanClone(detailOf(state.sel.id));
      focus.classList.add('tf-cu-focus'); focus.dataset.entity = state.sel.id;
      focus.querySelector('.tf-related')?.remove(); closeup.append(focus);
      const neighbors = document.createElement('ul'); neighbors.className = 'tf-cu-neighbors';
      visibleLinks().forEach(l => {
        const id = l.from === state.sel.id ? l.to : l.from;
        const item = document.createElement('li'); item.dataset.tier = l.tier;
        const button = document.createElement('button'); button.type = 'button';
        button.dataset.entity = id; button.textContent = entityName(id);
        item.append(button);
        const description = document.createElement('p');
        description.className = 'tf-cu-verb';
        description.append(cleanClone(l.li.querySelector('.tf-link-sel')));
        description.classList.add('tf-meta');
        description.append(cleanClone(l.li.querySelector('.tf-tierlabel')));
        item.append(description);
        item.append(cleanClone(l.li.querySelector('.tf-when')));
        const caveat = l.li.querySelector('.tf-caveat');
        if (caveat) item.append(cleanClone(caveat));
        const sources = document.createElement('p');
        sources.className = 'tf-meta';
        sources.append(cleanClone(l.li.querySelector('.tf-src')), cleanClone(l.li.querySelector('.tf-art')));
        item.append(sources); neighbors.append(item);
      });
      closeup.append(neighbors);
    } else if (state.all && !state.sel) {
      const list = document.createElement('ol'); list.className = 'tf-ledger';
      visibleLinks().forEach(l => list.append(cleanClone(l.li)));
      closeup.append(list);
    } else {
      [...panel.children].forEach(n => closeup.append(cleanClone(n)));
    }
  }
  function updateView() {
    const isPhone = phone.matches;
    root.dataset.mode = isPhone ? 'phone' : 'desktop';
    closeup.hidden = !isPhone || phoneView !== 'board';
    book.hidden = isPhone && phoneView !== 'list';
    panel.hidden = isPhone;
    root.querySelector('.tf-stage').hidden = isPhone && (!overviewOpen || phoneView !== 'board');
    root.querySelector('.tf-overview').hidden = !isPhone || phoneView !== 'board';
    root.querySelector('[data-overview="open"]').hidden = overviewOpen;
    root.querySelector('[data-overview="fit"]').hidden = !overviewOpen || overviewFit;
    root.querySelector('[data-overview="close"]').hidden = !overviewOpen;
    board.classList.toggle('is-open', isPhone && overviewOpen);
    board.classList.toggle('is-fit', isPhone && overviewFit);
    root.querySelectorAll('[data-view]').forEach(b => {
      b.setAttribute('aria-pressed', String(b.dataset.view === phoneView));
    });
  }
  function phoneDefault() {
    if (!phone.matches || state.sel || state.all) return;
    const first = board.querySelector('.tf-pin') || board.querySelector('[data-entity]');
    if (!first) return;
    state.sel = { type: 'e', id: first.dataset.entity };
    history.replaceState(null, '', toHash());
  }
  function refresh() {
    updateView(); fillPanel(); renderCloseup(); draw();
  }
  function toHash() {
    const p = new URLSearchParams();
    if (state.sel) p.set(state.sel.type, state.sel.id);
    if (state.all) {
      p.set('all', '1'); p.set('t', [...state.tiers].join(','));
      if (state.kinds) p.set('k', [...state.kinds].join(','));
      if (state.person) p.set('p', state.person);
    }
    return p.toString() ? '#' + p.toString() : '';
  }
  function fromHash() {
    const raw = location.hash.slice(1);
    const p = new URLSearchParams(raw);
    let sel = null;
    for (const t of ['e', 'l', 'z', 'g']) if (p.get(t)) sel = { type: t, id: p.get(t) };
    // Grāmatas saites ved uz #<id> (bez «=»): tā arī ir kartītes izvēle.
    if (!sel && raw && !raw.includes('=')) sel = bareSelection(raw);
    state.sel = valid(sel);
    state.all = p.get('all') === '1';
    state.tiers = new Set((p.has('t') ? p.get('t') : '1,2,3').split(',').filter(x => ['1', '2', '3'].includes(x)));
    state.kinds = p.has('k') ? new Set(p.get('k').split(',').filter(Boolean)) : null;
    state.person = nodeOf(p.get('p') || '')?.dataset.type === 'person' ? p.get('p') : '';
    phoneDefault(); syncControls(); refresh();
  }
  function commit(push = true) {
    const h = toHash();
    if (push) history.pushState(null, '', h || location.pathname + location.search);
    refresh();
  }
  function select(sel) {
    const fromPanel = panel.contains(document.activeElement);
    const fromCloseup = closeup.contains(document.activeElement);
    if (!fromPanel && !fromCloseup) lastFocus = document.activeElement;
    state.sel = valid(sel);
    if (phone.matches) phoneView = 'board';
    commit();
    if (fromPanel) panel.focus({ preventScroll: true });
    if (phone.matches) closeup.focus({ preventScroll: fromCloseup });
  }
  function bareSelection(raw) {
    let id;
    try { id = decodeURIComponent(raw); } catch { return null; }
    if (nodeOf(id)) return { type: 'e', id };
    if (id.startsWith('saite-')) return valid({ type: 'l', id: id.slice(6) });
    return null;
  }
  function syncControls() {
    const btn = root.querySelector('.tf-showall');
    btn.setAttribute('aria-pressed', String(state.all));
    root.querySelector('.tf-filters').hidden = !state.all;
    root.querySelectorAll('[data-filter-tier]').forEach(c => { c.checked = state.tiers.has(c.dataset.filterTier); });
    root.querySelectorAll('[data-filter-kind]').forEach(c => { c.checked = !state.kinds || state.kinds.has(c.dataset.filterKind); });
    const ps = root.querySelector('[data-filter-person]'); if (ps) ps.value = state.person;
  }

  board.addEventListener('click', e => {
    const n = e.target.closest('[data-entity]');
    if (n) return select({ type: 'e', id: n.dataset.entity });
    const z = e.target.closest('.tf-zone');
    if (z) return select({ type: 'z', id: z.dataset.zone });
  });
  // Diegi (SVG) nav fokusējami — tastatūras ekvivalents ir saites teikuma poga grāmatā un panelī.
  root.addEventListener('click', e => {
    const b = e.target.closest('[data-select-link]');
    if (b) return select({ type: 'l', id: b.dataset.selectLink });
    const a = e.target.closest('a[href^="#"]');
    const sel = a && bareSelection(a.getAttribute('href').slice(1));
    if (sel) { e.preventDefault(); select(sel); }
  });
  root.querySelectorAll('.tf-guide').forEach(g => g.addEventListener('click', () => select({ type: 'g', id: g.dataset.article })));
  root.querySelector('.tf-showall').addEventListener('click', () => { state.all = !state.all; state.sel = null; syncControls(); commit(); });
  root.querySelector('.tf-filters').addEventListener('change', () => {
    state.sel = null;
    state.tiers = new Set([...root.querySelectorAll('[data-filter-tier]:checked')].map(c => c.dataset.filterTier));
    const kinds = [...root.querySelectorAll('[data-filter-kind]')];
    state.kinds = kinds.every(c => c.checked) ? null : new Set(kinds.filter(c => c.checked).map(c => c.dataset.filterKind));
    state.person = root.querySelector('[data-filter-person]')?.value || '';
    commit();
  });
  closeup.addEventListener('click', e => {
    const button = e.target.closest('button[data-entity]');
    if (button) select({ type: 'e', id: button.dataset.entity });
  });
  closeup.addEventListener('change', e => {
    if (e.target.matches('[data-pick-entity]') && e.target.value) select({ type: 'e', id: e.target.value });
  });
  root.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => {
    phoneView = button.dataset.view; updateView(); draw();
  }));
  root.querySelectorAll('[data-overview]').forEach(button => button.addEventListener('click', () => {
    const action = button.dataset.overview;
    overviewOpen = action !== 'close'; overviewFit = action === 'fit';
    updateView(); draw();
    if (action === 'close') root.querySelector('[data-overview="open"]').focus();
    else root.querySelector('[data-overview="close"]').focus({ preventScroll: true });
  }));
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && state.sel) {
      state.sel = null; commit();
      (lastFocus?.isConnected && lastFocus.getClientRects().length
        ? lastFocus : root.querySelector('.tf-showall')).focus();
    }
  });
  window.addEventListener('popstate', fromHash);
  window.addEventListener('hashchange', fromHash);
  phone.addEventListener('change', () => { phoneDefault(); refresh(); });
  new ResizeObserver(() => draw()).observe(board);
  document.fonts?.ready.then(draw);
  fromHash();
})();
