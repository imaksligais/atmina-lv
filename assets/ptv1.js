// Partiju lapu klienta puses uzvedība (partijas.html + partija.html).
// Ārpus HTML pārcelts stingrai CSP (script-src bez 'unsafe-inline').

// --- partijas.html: koalīcijas/opozīcijas filtrs ---------------------------
// Deleģēts klikšķis uz [data-filter] pogas: iezīmē aktīvo pogu un rāda/slēpj
// partiju kartītes pēc data-coalition atribūta. (Iepriekš inline filterParties.)
document.addEventListener('click', function (e) {
  var btn = e.target.closest('.filter-bar [data-filter]');
  if (!btn) return;
  var filter = btn.getAttribute('data-filter');
  document.querySelectorAll('.filter-btn').forEach(function (b) {
    b.classList.remove('active');
    b.setAttribute('aria-pressed', 'false');
  });
  btn.classList.add('active');
  btn.setAttribute('aria-pressed', 'true');
  document.querySelectorAll('.party-card').forEach(function (card) {
    card.style.display = (filter === 'all' || card.dataset.coalition === filter) ? '' : 'none';
  });
});

// --- partija.html: profila cilnes ------------------------------------------
// Klase + ARIA + roving tabindex un bultas/Home/End — assets/tabs-v1.js
// (ielādēts pirms šī faila TIKAI partija.html; partijas.html nav ne joslas,
// ne tabs-v1.js → partyTabs = null).
var partyBar = document.querySelector('.profile-stats-bar');
var partyTabs = partyBar && window.atminaTabs({
  bar: partyBar,
  tab: '.profile-stat[data-tab]',
  activate: function (btn) { showPartyTab(btn.getAttribute('data-tab'), btn); },
});

// Rāda vienu .party-tab, iezīmē tās pogu. (Iepriekš inline showPartyTab.)
function showPartyTab(tab, btn) {
  document.querySelectorAll('.party-tab').forEach(function (t) { t.style.display = 'none'; });
  var panel = document.getElementById('tab-' + tab);
  if (panel) panel.style.display = '';
  if (partyTabs) partyTabs.select(btn);
}

// Deleģēts klikšķis uz [data-tab] profila pogas.
document.addEventListener('click', function (e) {
  var btn = e.target.closest('.profile-stats-bar .profile-stat[data-tab]');
  if (!btn) return;
  showPartyTab(btn.getAttribute('data-tab'), btn);
});

// Dziļā saite uz cilni caur #hash (piem., sintēzes "Programma" saite uz
// #programma). Aktivizē atbilstošo cilni + tās pogu ielādes brīdī.
// (Selektors pārrakstīts no [onclick*="showPartyTab..."] uz [data-tab="..."].)
document.addEventListener('DOMContentLoaded', function () {
  var tab = (location.hash || '').replace('#', '');
  if (!tab) return;
  var btn = document.querySelector(
    '.profile-stats-bar .profile-stat[data-tab="' + tab + '"]');
  if (btn && document.getElementById('tab-' + tab)) showPartyTab(tab, btn);
});
