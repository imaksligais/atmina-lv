// ms-a11y.js — tastatūras + ekrānlasītāja pieejamība pielāgotajiem
// multi-select nolaižamajiem filtriem (div-listbox raksts).
//
// Markā (templates) jau ir statiskie ARIA atribūti (role="listbox"/"option",
// aria-multiselectable, aria-haspopup, aria-expanded="false", aria-selected="false",
// tabindex). Šis fails pievieno DINAMISKO daļu:
//   • aria-controls saiti (paneļa id no vecāka .multi-select/.xv1-select id),
//   • aria-expanded / aria-selected sinhronizāciju ar .open / .selected klasēm
//     (caur MutationObserver — strādā neatkarīgi no tā, kurš JS pārslēdz klasi),
//   • tastatūras navigāciju (bultas, Enter/Space, Escape, Tab).
//
// Peles uzvedība un esošie inline klikšķu apstrādātāji NETIEK mainīti — Enter/Space
// deleģē uz .click(), tāpēc atkārtoti izmanto to pašu loģiku (atlase, filtri, etiķete).
(function () {
  "use strict";

  // Atbalstītās widžetu saimes — vienāda uzvedība, atšķiras tikai klašu nosaukumi.
  var CONFIGS = [
    {
      root: ".multi-select",
      trigger: ".multi-select-trigger",
      panel: ".multi-select-dropdown",
      option: ".multi-select-option",
      clear: ".multi-select-clear",
      search: ".multi-select-search",
    },
    {
      root: ".xv1-select",
      trigger: ".xv1-select-trigger",
      panel: ".xv1-select-dropdown",
      option: ".xv1-select-option",
      clear: ".xv1-select-clear",
      search: ".xv1-select-search",
    },
  ];

  CONFIGS.forEach(function (cfg) {
    var roots = document.querySelectorAll(cfg.root);
    for (var i = 0; i < roots.length; i++) {
      enhance(roots[i], cfg, i);
    }
  });

  // --- Deleģēta meklēšanas filtrēšana (aizstāj per-page inline filterOptions) ---
  // Stingrā CSP dēļ inline oninput="filterOptions(this)" atribūti tiek noņemti;
  // šeit viens document-līmeņa 'input' klausītājs pilda to pašu loģiku abām
  // widžetu saimēm (.multi-select-search un .xv1-select-search). Klašu nosaukumi
  // (dropdown/option) atvasināti no CONFIGS pēc tā, kura meklēšanas klase sakrita.
  // Papildinošs pret esošo per-page loģiku: displeja pārslēgšana ir idempotenta
  // (tīra funkcija no ievades vērtības), tāpēc dubulta izsaukšana nekaitē.
  document.addEventListener("input", function (e) {
    var input = e.target;
    for (var j = 0; j < CONFIGS.length; j++) {
      var cfg = CONFIGS[j];
      if (input.matches && input.matches(cfg.search)) {
        var q = input.value.toLowerCase();
        var dropdown = input.closest(cfg.panel);
        if (!dropdown) return;
        var opts = dropdown.querySelectorAll(cfg.option);
        for (var k = 0; k < opts.length; k++) {
          var opt = opts[k];
          opt.style.display =
            (!q || opt.textContent.toLowerCase().indexOf(q) !== -1) ? "" : "none";
        }
        return;
      }
    }
  });

  function enhance(root, cfg, index) {
    var trigger = root.querySelector(cfg.trigger);
    var panel = root.querySelector(cfg.panel);
    if (!trigger || !panel) return;
    var clear = root.querySelector(cfg.clear);
    var search = root.querySelector(cfg.search);

    // --- aria-controls: panelim vajag id ---
    if (!panel.id) panel.id = (root.id || cfg.root.slice(1) + "-" + index) + "-listbox";
    trigger.setAttribute("aria-controls", panel.id);
    if (!trigger.hasAttribute("aria-haspopup")) trigger.setAttribute("aria-haspopup", "listbox");

    // Paneļa pieejamais nosaukums no trigera redzamās etiķetes (bez bultas).
    if (!panel.hasAttribute("aria-label")) {
      var lbl = (trigger.textContent || "").replace(/[▼▾↓]/g, "").trim();
      if (lbl) panel.setAttribute("aria-label", lbl);
    }

    // --- aria-expanded sinhronizācija ar .open klasi uz saknes ---
    function isOpen() { return root.classList.contains("open"); }
    function syncExpanded() { trigger.setAttribute("aria-expanded", isOpen() ? "true" : "false"); }
    syncExpanded();
    new MutationObserver(syncExpanded).observe(root, {
      attributes: true, attributeFilter: ["class"],
    });

    // --- Opcijas: role/aria-selected/tabindex + aria-selected sinhronizācija ---
    function allOptions() {
      return Array.prototype.slice.call(root.querySelectorAll(cfg.option));
    }
    allOptions().forEach(function (opt) {
      if (!opt.hasAttribute("role")) opt.setAttribute("role", "option");
      if (!opt.hasAttribute("tabindex")) opt.setAttribute("tabindex", "-1");
      var sync = function () {
        opt.setAttribute("aria-selected", opt.classList.contains("selected") ? "true" : "false");
      };
      sync();
      new MutationObserver(sync).observe(opt, { attributes: true, attributeFilter: ["class"] });
    });

    if (clear && !clear.hasAttribute("role")) {
      clear.setAttribute("role", "button");
      clear.setAttribute("tabindex", "-1");
    }

    // Redzamās opcijas (respektē meklēšanas filtra display:none).
    function visibleOptions() {
      return allOptions().filter(function (o) { return o.style.display !== "none"; });
    }
    // Fokusa loks bultu navigācijai: redzamās opcijas + "Notīrīt".
    function focusRing() {
      var ring = visibleOptions();
      if (clear) ring.push(clear);
      return ring;
    }
    function focusAt(ring, idx) {
      if (!ring.length) return;
      if (idx < 0) idx = ring.length - 1;
      else if (idx >= ring.length) idx = 0;
      ring[idx].focus();
    }

    function openPanel() {
      if (isOpen()) return;
      // Aizver citas atvērtās tās pašas saimes izvēlnes (kā inline uzvedība).
      document.querySelectorAll(cfg.root + ".open").forEach(function (s) {
        if (s !== root) s.classList.remove("open");
      });
      root.classList.add("open");
    }
    function closePanel(focusTrigger) {
      root.classList.remove("open");
      if (focusTrigger) trigger.focus();
    }

    // --- Trigera tastatūra ---
    trigger.addEventListener("keydown", function (e) {
      var k = e.key;
      if (k === "Enter" || k === " " || k === "Spacebar") {
        // Īsts <button> Enter/Space jau izsauc click natīvi; div (role=button) — nē.
        if (trigger.tagName !== "BUTTON") {
          e.preventDefault();
          trigger.click(); // inline apstrādātājs pārslēdz .open (+ fokusē meklēšanu)
        }
      } else if (k === "ArrowDown") {
        e.preventDefault();
        openPanel();
        setTimeout(function () { focusAt(focusRing(), 0); }, 0);
      } else if (k === "Escape") {
        if (isOpen()) { e.preventDefault(); closePanel(true); }
      }
    });

    // --- Meklēšanas ievade: ArrowDown → pirmā opcija; Escape/Tab → aizver ---
    if (search) {
      search.addEventListener("keydown", function (e) {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          focusAt(visibleOptions(), 0);
        } else if (e.key === "Escape") {
          e.preventDefault();
          closePanel(true);
        } else if (e.key === "Tab") {
          closePanel(false); // ļauj Tab dabiski pāriet tālāk
        }
      });
    }

    // --- Opciju / "Notīrīt" tastatūra (deleģēts uz saknes) ---
    root.addEventListener("keydown", function (e) {
      var target = e.target;
      var onOption = target.closest && target.closest(cfg.option);
      var onClear = clear && target === clear;
      if (!onOption && !onClear) return; // trigeris/meklēšana apstrādā paši
      var ring = focusRing();
      var idx = ring.indexOf(target);
      var k = e.key;
      if (k === "ArrowDown") {
        e.preventDefault();
        focusAt(ring, idx + 1);
      } else if (k === "ArrowUp") {
        e.preventDefault();
        focusAt(ring, idx - 1);
      } else if (k === "Home") {
        e.preventDefault();
        focusAt(ring, 0);
      } else if (k === "End") {
        e.preventDefault();
        focusAt(ring, ring.length - 1);
      } else if (k === "Enter" || k === " " || k === "Spacebar") {
        // Pārslēdz fokusēto opciju (vai izpilda "Notīrīt"); panelis paliek atvērts,
        // atbilstoši peles uzvedībai (multi-select).
        e.preventDefault();
        target.click();
      } else if (k === "Escape") {
        e.preventDefault();
        closePanel(true);
      } else if (k === "Tab") {
        closePanel(false); // aizver un ļauj Tab pāriet dabiski
      }
    });
  }
})();
