// Politiķa profila lapa (politiki/<slug>.html) — cilņu pārslēgšana (pele,
// pieskāriens, klaviatūra), URL hash deep-link, pozīciju tēmu filtrs un VAD
// gada-cilņu pārslēgšana.
// Pārcelts no inline <script> uz ārēju failu (stingrs CSP: script-src bez
// 'unsafe-inline', 2026-07-23).
//
// Adreses forma: politiki/<slug>.html?tema=<URL-kodēta tēma>#pozicijas —
// hash nes cilni, ?tema= pozīciju tēmas filtru (2026-09-05). Abus validē
// pret lapā esošo (cilņu JSON bloks, #topic-filter pogas); nezināma vērtība
// → noklusētā cilne / "Visas tēmas".

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

  var statsBar = document.querySelector(".profile-stats-bar");

  // Cilņu pogas dokumenta secībā — bultu navigācijas kārtība.
  function tabButtons() {
    if (!statsBar) return [];
    return Array.prototype.slice.call(statsBar.querySelectorAll("[data-tab]"));
  }

  // Ieritina cilni JOSLĀ, mainot TIKAI joslas horizontālo scrollLeft.
  // Apzināti nav `scrollIntoView` — tas ritina arī tuvāko vertikālo
  // konteineru, un mobilajā hash-ielādē lapa pielēktu (T3, 2026-09-05).
  function scrollTabIntoView(btn) {
    if (!statsBar || !btn || typeof btn.getBoundingClientRect !== "function") return;
    var bar = statsBar.getBoundingClientRect();
    var box = btn.getBoundingClientRect();
    if (box.left < bar.left) statsBar.scrollLeft += box.left - bar.left;
    else if (box.right > bar.right) statsBar.scrollLeft += box.right - bar.right;
  }

  // Pārslēdz redzamo cilni un sinhronizē stat-bar pogu stāvokli. ``btn`` ir
  // attiecīgā cilnes poga (vai null, ja izsaukts bez konteksta).
  function showProfileTab(tab, btn) {
    document.querySelectorAll(".profile-tab").forEach(function (t) { t.style.display = "none"; });
    document.querySelectorAll(".profile-stats-bar .profile-stat").forEach(function (b) {
      b.classList.remove("active");
      b.setAttribute("aria-selected", "false");
      // Roving tabindex: tabulācijas secībā paliek tikai aktīvā cilne.
      // Bez ``btn`` (izsaukums bez pogas konteksta) tabindex NEaiztiekam —
      // citādi joslā nepaliktu neviena cilne tabulācijas secībā.
      if (btn) b.setAttribute("tabindex", "-1");
    });
    var el = document.getElementById("tab-" + tab);
    if (el) el.style.display = "";
    if (btn) {
      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
      btn.setAttribute("tabindex", "0");
      scrollTabIntoView(btn);
    }
    // Sinhronizē URL hash bez page reload — ļauj kopēt deep-link uz cilni.
    if (window.history && window.history.replaceState) {
      window.history.replaceState(null, "", "#" + tab);
    }
  }

  // Deleģēts klikšķis uz cilņu joslas [data-tab] pogām (aizvieto katras
  // pogas onclick="showProfileTab(...)").
  if (statsBar) {
    statsBar.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-tab]");
      if (!btn || !statsBar.contains(btn)) return;
      showProfileTab(btn.dataset.tab, btn);
    });

    // Klaviatūra (WAI-ARIA tabs, automatic activation): bultas pa kreisi/
    // pa labi ar apliekšanos, Home/End uz pirmo/pēdējo. `ms-a11y.js`
    // apkalpo listbox/opcijas, NE role="tab" — tāpēc šis kods ir šeit,
    // uz tā paša showProfileTab ceļa, nevis atsevišķs handleris.
    statsBar.addEventListener("keydown", function (e) {
      var btns = tabButtons();
      var cur = btns.indexOf(document.activeElement);
      if (cur < 0 || btns.length === 0) return;
      var next;
      if (e.key === "ArrowRight") next = (cur + 1) % btns.length;
      else if (e.key === "ArrowLeft") next = (cur - 1 + btns.length) % btns.length;
      else if (e.key === "Home") next = 0;
      else if (e.key === "End") next = btns.length - 1;
      else return;
      e.preventDefault();
      showProfileTab(btns[next].dataset.tab, btns[next]);
      // preventScroll → fokuss nepārvieto lapu; joslu ieritina
      // scrollTabIntoView (tikai horizontāli).
      try { btns[next].focus({ preventScroll: true }); } catch (err) { btns[next].focus(); }
      scrollTabIntoView(btns[next]);
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
    // Pārskata tēmu čips nes arī data-topic → papildus cilnei uzliek
    // Pozīciju tēmas filtru un ieraksta to adresē (?tema=). Enkurs bez
    // data-topic (pārējie tab-link) filtru neaiztiek.
    if (link.dataset.topic) setTopic(link.dataset.topic, true);
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

  // Atrod tēmas pogu pēc PRECĪZAS data-filter vērtības, pārstaigājot
  // pogu sarakstu. Apzināti nav querySelector ar interpolētu vērtību —
  // URL vai čipa tēma tā nekad nenonāk CSS selektorā.
  function topicButton(topic) {
    if (!topicFilter) return null;
    var btns = topicFilter.querySelectorAll(".filter-btn");
    for (var i = 0; i < btns.length; i++) {
      if (btns[i].dataset.filter === topic) return btns[i];
    }
    return null;
  }

  // Sinhronizē ?tema= ar aktīvo filtru: saglabā pārējos URL parametrus
  // un hash, "Visas tēmas" (all) parametru noņem. Tā pati replaceState
  // pieeja kā cilnēm — bez maršrutētāja.
  function syncTopicParam(topic) {
    if (!window.history || !window.history.replaceState) return;
    try {
      var url = new URL(window.location.href);
      if (topic && topic !== "all") url.searchParams.set("tema", topic);
      else url.searchParams.delete("tema");
      window.history.replaceState(null, "", url.href);
    } catch (e) { /* URL/replaceState nav pieejams → adrese paliek, filtrs strādā */ }
  }

  // Uzliek tēmas filtru un sinhronizē pogu stāvokli. Nezināma tēma →
  // "Visas tēmas" (kluss fallback). ``syncUrl`` false pie lapas ielādes,
  // kur adrese jau ir lasītāja dotā.
  // Sakļautās (retās) tēmu pogas — «Vēl N tēmas» tās atklāj; deep-link
  // uz sakļautu tēmu tās atklāj pats, lai aktīvā poga nav neredzama.
  function revealTopicButtons() {
    if (!topicFilter) return;
    topicFilter.querySelectorAll(".topic-filter-more").forEach(function (b) { b.hidden = false; });
    var toggle = topicFilter.querySelector("[data-topic-more-toggle]");
    if (toggle) { toggle.hidden = true; toggle.setAttribute("aria-expanded", "true"); }
  }

  function setTopic(topic, syncUrl) {
    var btn = topicButton(topic);
    if (!btn) {
      topic = "all";
      btn = topicButton("all");
    }
    if (btn && btn.hidden) revealTopicButtons();
    if (topicFilter) {
      topicFilter.querySelectorAll(".filter-btn").forEach(function (b) {
        b.classList.remove("active");
        b.setAttribute("aria-pressed", "false");
      });
      if (btn) {
        btn.classList.add("active");
        btn.setAttribute("aria-pressed", "true");
      }
    }
    activeTopic = topic;
    applyClaimFilters();
    if (syncUrl) syncTopicParam(topic);
  }

  if (topicFilter) {
    topicFilter.addEventListener("click", function (e) {
      if (e.target.closest("[data-topic-more-toggle]")) { revealTopicButtons(); return; }
      var fb = e.target.closest(".filter-btn");
      if (!fb || !topicFilter.contains(fb)) return;
      setTopic(fb.dataset.filter, true);
    });
  }

  // Page-load ?tema= atbalsts — tēmu validē pret profilā esošajām filtra
  // pogām (nezināma → "Visas tēmas"). Adresi šeit NEpārrakstām; nākamā
  // filtra maiņa to sakārto.
  if (topicFilter && window.URLSearchParams) {
    try {
      var temaParam = new URLSearchParams(window.location.search).get("tema");
      if (temaParam) setTopic(temaParam, false);
    } catch (e) { /* bojāts query → filtrs paliek "Visas tēmas" */ }
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
