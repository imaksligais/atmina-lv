// Atradumi: politiķa vārds tekstā (a.pol-link) → viens kopīgs lodziņš #pol-pop.
// Stāvokļa mašīna kā blv1.js sēdvietu lodziņam: pele (hover ierīcē UN
// pointerType 'mouse') atver, uzbraucot, klikšķis ar peli → profils.
// Pieskāriens/pildspalva atver lodziņu ar «Profils →» un NEnavigē.
// popover="auto": Esc un pieskāriens citur aizver pārlūks pats. Bez JS vai
// bez popover atbalsta — parasta saite uz profilu.
(function() {
  var pop = document.getElementById('pol-pop');
  if (!pop || !pop.showPopover) return;
  var state = { link: null, mode: null, timer: null };
  var lastPointer = '';
  var canHover = window.matchMedia ? window.matchMedia('(hover: hover) and (pointer: fine)') : null;
  var SEL = 'a.pol-link';

  function clearTimer() {
    if (state.timer) { clearTimeout(state.timer); state.timer = null; }
  }
  function resetState() {
    clearTimer();
    if (state.link) state.link.classList.remove('is-pol-active');
    state.link = null;
    state.mode = null;
  }
  function closePop() {
    if (pop.matches(':popover-open')) pop.hidePopover();
    resetState();
  }
  function line(cls, text) {
    var p = document.createElement('p');
    p.className = cls;
    p.textContent = text;
    return p;
  }
  function fill(link) {
    var d = link.dataset;
    var face;
    if (d.photo) {
      face = document.createElement('img');
      face.src = d.photo;
      face.alt = '';
      face.width = 48;
      face.height = 48;
    } else {
      face = document.createElement('span');
      face.className = 'pol-pop-initials';
      face.textContent = d.initials || '';
      face.setAttribute('aria-hidden', 'true');
    }
    face.classList.add('pol-pop-face');
    var nodes = [face, line('seat-pop-name', link.textContent)];
    if (d.party) {
      var party = line('pol-pop-party', d.party);
      if (d.color) party.style.setProperty('--party', d.color);
      nodes.push(party);
    }
    if (d.role) nodes.push(line('pol-pop-role', d.role));
    if (d.stats) nodes.push(line('pol-pop-stats', d.stats));
    var a = document.createElement('a');
    a.className = 'seat-pop-link';
    a.href = link.href;
    a.textContent = 'Profils →';
    nodes.push(a);
    if (pop.dataset.asof) nodes.push(line('pol-pop-asof', 'dati uz ' + pop.dataset.asof));
    pop.replaceChildren.apply(pop, nodes);
  }
  function openFor(link, mode) {
    clearTimer();
    var open = pop.matches(':popover-open');
    if (open && state.link === link) { state.mode = mode; return; }
    // Atvērtam lodziņam atkārtots showPopover enkuru NEpārceļ — vispirms aizver.
    if (open) pop.hidePopover();
    resetState();
    fill(link);
    try { pop.showPopover({ source: link }); } catch (err) { pop.showPopover(); }
    state.link = link;
    state.mode = mode;
    link.classList.add('is-pol-active');
  }
  function scheduleClose() {
    if (state.mode !== 'hover') return;
    clearTimer();
    state.timer = setTimeout(closePop, 200);
  }

  document.addEventListener('pointerdown', function(e) { lastPointer = e.pointerType || ''; });
  document.addEventListener('pointerover', function(e) {
    var link = e.target.closest && e.target.closest(SEL);
    if (!link || e.pointerType !== 'mouse' || !canHover || !canHover.matches) return;
    openFor(link, 'hover');
  });
  document.addEventListener('pointerout', function(e) {
    if (e.pointerType !== 'mouse') return;
    var link = e.target.closest && e.target.closest(SEL);
    if (link && link === state.link && !link.contains(e.relatedTarget)) scheduleClose();
  });
  document.addEventListener('click', function(e) {
    var link = e.target.closest && e.target.closest(SEL);
    if (!link) return;
    // Tastatūra, jauna cilne vai ne-kreisā poga — parasta saite.
    if (e.detail === 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.button) return;
    if ((e.pointerType || lastPointer) === 'mouse') return;
    e.preventDefault();
    openFor(link, 'tap');
  });
  // Kursors uz paša lodziņa (lai var noklikšķināt saiti) aizvēršanu atceļ.
  pop.addEventListener('pointerover', clearTimer);
  pop.addEventListener('pointerout', function(e) {
    if (e.pointerType === 'mouse' && !pop.contains(e.relatedTarget)) scheduleClose();
  });
  pop.addEventListener('toggle', function(e) {
    if (e.newState === 'closed' && !pop.matches(':popover-open')) resetState();
  });
})();
