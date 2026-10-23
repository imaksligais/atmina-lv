// tabs-v1.js — kopīgs cilņu ARIA kontrakts lapām ar cilnēm (Analīzes,
// Balsojumi, partijas lapa).
//
// Kontrakts ir profila cilņu (`pp-tabs`, assets/ppv1.js) kontrakts:
// role=tablist/tab/tabpanel, aria-selected sinhronā ar `active` klasi,
// roving tabindex (tabulācijas secībā tikai aktīvā cilne) un WAI-ARIA
// tastatūra ar automātisku aktivizāciju — bultas pa kreisi/pa labi ar
// apliekšanos, Home/End uz pirmo/pēdējo. Profils šo failu NElieto: tā
// tastatūras ceļš sapīts ar hash, joslas ritināšanu un paneļa atklāšanu.
//
// Ko cilne parāda (paneļi, slinka inicializācija, hash), lemj lapa pati
// caur activate; lapas pārslēgšanas funkcija izsauc api.select(btn).
//
// Lietojums (ielādē PIRMS lapas skripta):
//   var tabs = window.atminaTabs({
//     bar: document.querySelector('.subtab-bar'),  // role="tablist" elements
//     tab: '.subtab-btn',                          // cilnes pogas selektors joslā
//     activate: function (btn) { switchTab(btn.dataset.tab); },
//   });
//   tabs.select(btn);   // atzīmē btn kā atlasīto (klase + ARIA + tabindex)
// Atgriež null, ja joslas nav lapā.
(function () {
  "use strict";

  window.atminaTabs = function (cfg) {
    var bar = cfg.bar;
    if (!bar) return null;

    function tabs() {
      return Array.prototype.slice.call(bar.querySelectorAll(cfg.tab));
    }

    function select(btn) {
      if (!btn) return;
      tabs().forEach(function (b) {
        var on = b === btn;
        b.classList.toggle("active", on);
        b.setAttribute("aria-selected", on ? "true" : "false");
        b.setAttribute("tabindex", on ? "0" : "-1");
      });
    }

    bar.addEventListener("keydown", function (e) {
      var btns = tabs();
      var cur = btns.indexOf(document.activeElement);
      if (cur < 0 || btns.length === 0) return;
      var next;
      if (e.key === "ArrowRight") next = (cur + 1) % btns.length;
      else if (e.key === "ArrowLeft") next = (cur - 1 + btns.length) % btns.length;
      else if (e.key === "Home") next = 0;
      else if (e.key === "End") next = btns.length - 1;
      else return;
      e.preventDefault();
      cfg.activate(btns[next]);
      // Bez preventScroll: šīs joslas nav sticky, un pārlūks pats ieritina
      // šauru (390 px) joslu līdz fokusētajai cilnei.
      btns[next].focus();
    });

    return { select: select, tabs: tabs };
  };
})();
