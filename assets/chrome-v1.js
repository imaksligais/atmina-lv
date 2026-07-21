// chrome-v1.js — vietnes chrome mijiedarbība (tēmas pārslēgs, skaņu slēdzis,
// burger izvēlne, "Vairāk" atklājējs, kopēšanas pogas, kartīšu navigācija).
// Izcelts no base.html.j2 stingrās CSP dēļ (script-src bez 'unsafe-inline').
//
// cuelume dinamiskā importa URL atvasinām no paša skripta atrašanās vietas:
// document.currentScript ir null aizkavētos (deferred) callback'os, tāpēc to
// noķeram sinhroni moduļa augšpusē. chrome-v1.js dzīvo assets/, cuelume —
// assets/cuelume/, tāpēc relatīvā atrisināšana pret skripta URL dod pareizo ceļu.
var chromeSrc = document.currentScript && document.currentScript.src;

(function () {
  var themeBtn = document.getElementById('nav-theme');
  if (themeBtn) {
    var syncThemeBtn = function (light) {
      themeBtn.setAttribute('aria-checked', String(light));
      var meta = document.getElementById('meta-theme-color');
      if (meta) meta.setAttribute('content', light ? '#f7f3e8' : '#0d1014');
      var cs = document.getElementById('meta-color-scheme');
      if (cs) cs.setAttribute('content', light ? 'light' : 'dark');
    };
    syncThemeBtn(document.documentElement.getAttribute('data-theme') === 'light');
    themeBtn.addEventListener('click', function () {
      var light = document.documentElement.getAttribute('data-theme') !== 'light';
      if (light) {
        document.documentElement.setAttribute('data-theme', 'light');
      } else {
        document.documentElement.removeAttribute('data-theme');
      }
      var theme = light ? 'light' : 'dark';
      try { localStorage.setItem('atmina:theme', theme); } catch (e) {}
      syncThemeBtn(light);
      document.dispatchEvent(new CustomEvent('atmina:themechange', { detail: { theme: theme } }));
    });
  }
  // Skaņu efekti — opt-in (default OFF, glabāts localStorage 'atmina:sound').
  // cuelume tiek ielādēts TIKAI ar lēno dynamic import, kad skaņa ieslēgta —
  // nulle izmaksu, kamēr lietotājs to nav apzināti aktivizējis.
  var sndBtn = document.getElementById('nav-sound');
  if (sndBtn) {
    var sndOn = false;
    try { sndOn = localStorage.getItem('atmina:sound') === 'on'; } catch (e) {}
    var cue = null;
    var loadCue = function () {
      return import(new URL('cuelume/index.js', chromeSrc).href).then(function (m) {
        cue = m; m.setEnabled(true); return m;
      });
    };
    var syncSndBtn = function () { sndBtn.setAttribute('aria-checked', String(sndOn)); };
    syncSndBtn();
    if (sndOn) loadCue();
    sndBtn.addEventListener('click', function () {
      sndOn = !sndOn;
      try { localStorage.setItem('atmina:sound', sndOn ? 'on' : 'off'); } catch (e) {}
      syncSndBtn();
      if (sndOn) { loadCue().then(function (m) { m.play('ready'); }); }
      else if (cue) { cue.setEnabled(false); }
    });
    document.addEventListener('atmina:themechange', function () { if (sndOn && cue) cue.play('toggle'); });
    document.addEventListener('atmina:copied', function () { if (sndOn && cue) cue.play('success'); });
    // Tabu pārslēgšana + izvēlnes atvēršana -> īss 'tick';
    // nav joslas un iekšējā satura navigācija -> 'page'.
    // Ārējie avotu linki, enkuri un kopēšanas poga paliek klusi.
    document.addEventListener('click', function (e) {
      if (!sndOn || !cue) return;
      if (e.target.closest('[role="tab"], .profile-stat, .nav-burger')) { cue.play('tick'); return; }
      var a = e.target.closest('main a[href], #nav-menu a[href]');
      if (!a || a.classList.contains('share-btn-copy')) return;
      var href = a.getAttribute('href');
      if (!href || href.charAt(0) === '#' || /^https?:/i.test(href)) return;
      cue.play('page');
    });
  }
  var nav = document.querySelector('.nav');
  var burger = document.getElementById('nav-burger');
  var menu = document.getElementById('nav-menu');
  if (!nav || !menu) return;
  function setOpen(open) {
    nav.classList.toggle('nav-open', open);
    if (burger) {
      burger.setAttribute('aria-expanded', String(open));
      burger.setAttribute('aria-label', open ? 'Aizvērt izvēlni' : 'Atvērt izvēlni');
    }
  }
  if (burger) burger.addEventListener('click', function () {
    setOpen(!nav.classList.contains('nav-open'));
  });
  // Close the mobile overlay when a real link is tapped.
  menu.addEventListener('click', function (e) {
    if (e.target.closest('a')) setOpen(false);
  });
  // "Vairāk" disclosure — click toggles on touch/desktop; CSS handles hover.
  var more = menu.querySelector('.nav-more-btn');
  if (more) {
    more.addEventListener('click', function (e) {
      e.stopPropagation();
      // stopPropagation bloķē document-līmeņa skaņas handleri — spēlējam
      // tieši šeit (sndOn/cue ir IIFE funkcijas scope caur var hoisting).
      if (sndOn && cue) cue.play('tick');
      var open = more.getAttribute('aria-expanded') === 'true';
      more.setAttribute('aria-expanded', String(!open));
      more.parentNode.classList.toggle('is-open', !open);
    });
    document.addEventListener('click', function (e) {
      if (!more.parentNode.contains(e.target)) {
        more.setAttribute('aria-expanded', 'false');
        more.parentNode.classList.remove('is-open');
      }
    });
  }
})();

// Copy-to-clipboard share buttons ([data-copy-url]) — profiles, topics, etc.
document.addEventListener('click', function (e) {
  var btn = e.target.closest('.share-btn-copy');
  if (!btn) return;
  e.preventDefault();
  var url = btn.getAttribute('data-copy-url') || window.location.href;
  var done = function () {
    var prev = btn.getAttribute('data-label') || btn.textContent;
    btn.setAttribute('data-label', prev);
    btn.textContent = 'Nokopēts!';
    btn.classList.add('is-copied');
    try { document.dispatchEvent(new CustomEvent('atmina:copied')); } catch (err) {}
    setTimeout(function () { btn.textContent = prev; btn.classList.remove('is-copied'); }, 1600);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(done, done);
  } else {
    var ta = document.createElement('textarea');
    ta.value = url; document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); } catch (err) { /* no-op */ }
    document.body.removeChild(ta); done();
  }
});

// Vispārīga kartīšu navigācija: klikšķis uz [data-card-href] elementa aizved uz
// norādīto URL, JA klikšķis nav uz iekšēja <a> (lai kartītē esošās saites
// strādā normāli, nevis tiek pārrakstītas). Aizstāj per-card
// onclick="window.location=..." + iekšējo saišu event.stopPropagation() atribūtus,
// ko stingrā CSP bloķētu.
document.addEventListener('click', function (e) {
  var card = e.target.closest('[data-card-href]');
  if (!card) return;
  if (e.target.closest('a')) return;
  window.location = card.getAttribute('data-card-href');
});
