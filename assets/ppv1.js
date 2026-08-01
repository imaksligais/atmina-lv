// Politiķa profila lapa (politiki/<slug>.html) — cilņu pārslēgšana,
// URL hash deep-link, pozīciju tēmu filtrs un VAD gada-cilņu pārslēgšana.
// Pārcelts no inline <script> uz ārēju failu (stingrs CSP: script-src bez
// 'unsafe-inline', 2026-07-23). Uzvedība identiska agrākajam inline kodam.

(function () {
  "use strict";

  // Pieejamo cilņu kopa — nolasīta no #profile-tabs JSON bloka (saglabā
  // tab_set secību), ļauj validēt URL hash pret esošajām cilnēm.
  var tabsEl = document.getElementById("profile-tabs");
  var validTabs = new Set();
  if (tabsEl) {
    try {
      var arr = JSON.parse(tabsEl.textContent);
      if (Array.isArray(arr)) {
        arr.forEach(function (t) { validTabs.add(t); });
      }
    } catch (e) { /* tukšs / bojāts bloks → nav validu cilņu */ }
  }

  // Pārslēdz redzamo cilni un sinhronizē stat-bar pogu stāvokli. ``btn`` ir
  // attiecīgā cilnes poga (vai null, ja izsaukts bez konteksta).
  function showProfileTab(tab, btn) {
    document.querySelectorAll(".profile-tab").forEach(function (t) { t.style.display = "none"; });
    document.querySelectorAll(".profile-stats-bar .profile-stat").forEach(function (b) {
      b.classList.remove("active");
      b.setAttribute("aria-selected", "false");
    });
    var el = document.getElementById("tab-" + tab);
    if (el) el.style.display = "";
    if (btn) {
      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
    }
    // Sinhronizē URL hash bez page reload — ļauj kopēt deep-link uz cilni.
    if (window.history && window.history.replaceState) {
      window.history.replaceState(null, "", "#" + tab);
    }
  }

  // Deleģēts klikšķis uz cilņu joslas [data-tab] pogām (aizvieto katras
  // pogas onclick="showProfileTab(...)").
  var statsBar = document.querySelector(".profile-stats-bar");
  if (statsBar) {
    statsBar.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-tab]");
      if (!btn || !statsBar.contains(btn)) return;
      showProfileTab(btn.dataset.tab, btn);
    });
  }

  // Deleģēts klikšķis uz [data-tab-link] enkuriem (Pārskata tēmu čipi):
  // aktivizē nosaukto cilni tāpat kā agrākais čipa onclick — atrod
  // atbilstošo stat-bar pogu un pārslēdz uz to (+ return false → nav
  // noklusētās enkura navigācijas).
  document.addEventListener("click", function (e) {
    var link = e.target.closest("[data-tab-link]");
    if (!link) return;
    e.preventDefault();
    var tab = link.dataset.tabLink;
    var tabBtn = document.querySelector('.profile-stats-bar [data-tab="' + tab + '"]');
    showProfileTab(tab, tabBtn);
  });

  // Page-load URL hash atbalsts — ja hash mērķē uz redzamu cilni,
  // aktivizē to override'ojot default. Hash uz neredzamu cilni → silent
  // fallback uz default (default cilnes button jau aktīvs HTML pusē).
  var hash = (window.location.hash || "").replace(/^#/, "");
  if (hash && validTabs.has(hash)) {
    var hashBtn = document.querySelector('.profile-stats-bar [data-tab="' + hash + '"]');
    if (hashBtn) showProfileTab(hash, hashBtn);
  }

  // Pozīciju tabulas tēmu filtrs.
  var topicFilter = document.getElementById("topic-filter");
  var claimRows = document.querySelectorAll("#claims-table tbody tr");
  var activeTopic = "all";

  function applyClaimFilters() {
    claimRows.forEach(function (row) {
      var matchTopic = activeTopic === "all" || row.dataset.topic === activeTopic;
      row.style.display = matchTopic ? "" : "none";
    });
  }

  if (topicFilter) {
    topicFilter.addEventListener("click", function (e) {
      if (!e.target.classList.contains("filter-btn")) return;
      topicFilter.querySelectorAll(".filter-btn").forEach(function (b) {
        b.classList.remove("active");
        b.setAttribute("aria-pressed", "false");
      });
      e.target.classList.add("active");
      e.target.setAttribute("aria-pressed", "true");
      activeTopic = e.target.dataset.filter;
      applyClaimFilters();
    });
  }

  // VAD gada-cilņu pārslēgšana (Deklarācijas cilne, _vad_panel.html.j2):
  // deleģēts klikšķis uz [data-decl-id] pogām (aizvieto agrāko inline
  // showVadYear). VAD panelis parādās tikai profila lapā.
  document.addEventListener("click", function (e) {
    var yearBtn = e.target.closest(".vad-year-tab[data-decl-id]");
    if (!yearBtn) return;
    var declId = yearBtn.dataset.declId;
    document.querySelectorAll(".vad-decl").forEach(function (d) { d.style.display = "none"; });
    document.querySelectorAll(".vad-year-tab").forEach(function (t) { t.classList.remove("active"); });
    var panel = document.getElementById("vad-decl-" + declId);
    if (panel) panel.style.display = "";
    yearBtn.classList.add("active");
  });
})();
