// Pozīcijas V2 — filter rail + dense table + client-side pagination.
// Runs on /pozicijas.html. Data fetched from /pozicijas-data.json (split
// from HTML 2026-04-25 to drop initial HTML weight 616KB→78KB so server
// dynamic compression is faster). Backward-compat: window._pzData inline
// still honored if present (test harness, future inline fallback).
//
// Tuple order (13 fields):
//   [topic, party, partyShort, partyColor, person, slug,
//    stanceText, dateISO, sourceUrl, sourceDomain, confidence, confidenceTier,
//    quote]
// quote (2026-07-22) ir verbatim citāts — tikai meklēšanas haystack'am, netiek
// renderēts tabulā. Guard ar || "" ļauj JS strādāt arī ar veco 12-lauku JSON.

(function () {
  "use strict";

  // --- Tuple index constants ---
  const IDX_TOPIC = 0, IDX_PARTY = 1, IDX_PARTY_SHORT = 2, IDX_PARTY_COLOR = 3,
        IDX_PERSON = 4, IDX_SLUG = 5, IDX_STANCE = 6, IDX_DATE = 7,
        IDX_SOURCE_URL = 8, IDX_SOURCE_DOMAIN = 9,
        IDX_CONF = 10, IDX_CONF_TIER = 11, IDX_QUOTE = 12;

  const PAGE_SIZE = 50;

  // --- State ---
  const pzState = {
    topic: "visas",
    party: "Visas",
    persons: new Set(),
    period: "visi",       // visi | nedela | menesis | gads
    confidence: "visas",  // visas | augsta | laba
    query: "",
    sort: "date",         // date | confidence | topic
    page: 1,
  };

  // Late-bound — populated either from inline window._pzData OR from
  // fetched pozicijas-data.json. All consumers reference the closure
  // variable, so reassignment from initData() propagates everywhere.
  let data = [];

  // --- Elements ---
  const rowsEl = document.getElementById("pzv1-rows");
  const paginationEl = document.getElementById("pzv1-pagination");
  const shownEl = document.getElementById("pzv1-shown");
  const searchEl = document.getElementById("pzv1-search");
  const clearEl = document.getElementById("pzv1-clear");
  if (!rowsEl) return;

  // --- Utilities ---
  function esc(s) {
    if (s == null) return "";
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // Diakritiku locīšana kā sgv1.js — "bistami" atrod "bīstami". NFD sadala
  // ā/š/ņ… par bāzes burtu + kombinējošo zīmi, ko izmetam.
  function fold(s) {
    return String(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }

  // Meklēšanas haystack (persona+tēma+stance+citāts, folded) — kešots per
  // rinda, jo fold() pār 4.6k rindām uz katru taustiņsitienu ir dārgs.
  const hayCache = new WeakMap();
  function rowHay(c) {
    let h = hayCache.get(c);
    if (h === undefined) {
      // Interpunkciju aizstāj ar atstarpi un pieliek vadošo atstarpi — tā
      // tokens " vārds" sakrīt tikai ar VĀRDA SĀKUMU. Bez tā "trakais"
      // atrada "ātrākais" (folded "atrakais" satur "trakais"; 2026-07-22).
      h = " " + fold(c[IDX_PERSON] + " " + c[IDX_TOPIC] + " " + c[IDX_STANCE]
        + " " + (c[IDX_QUOTE] || "")).replace(/[^\p{L}\p{N}]+/gu, " ");
      hayCache.set(c, h);
    }
    return h;
  }

  // Vaicājuma tokeni, memoizēti pēc query vērtības — skaitās vienreiz per
  // izmaiņu, ne per rindu.
  let _tokQ = null, _toks = [];
  function queryTokens() {
    if (pzState.query !== _tokQ) {
      _tokQ = pzState.query;
      // " " prefikss katram tokenam = vārda-sākuma enkurs pret rowHay formātu.
      _toks = fold(_tokQ).split(/[^\p{L}\p{N}]+/u).filter(Boolean).map(t => " " + t);
    }
    return _toks;
  }

  function topicColorFor(topic) {
    // Look up color from the rail button that carries data-color.
    const btn = document.querySelector(`#pzv1-rail-topics .pzv1-rail-row[data-value="${CSS.escape(topic)}"]`);
    return (btn && btn.dataset.color) || "";
  }

  // --- Rendering ---
  function render() {
    const filtered = filterAndSort();
    renderRows(filtered);
    renderPagination(filtered.length);
    renderShownCount(filtered.length);
    renderActiveClear();
    updateFacetedCounts();
    renderMobileFilterState();
  }

  // --- Mobile filter state (chips + count) ---
  const DEFAULT_VALUES = {
    topic: "visas",
    party: "Visas",
    period: "visi",
    confidence: "visas",
  };
  const AXIS_LABELS = {
    topic: "Tēma",
    party: "Partija",
    period: "Periods",
    confidence: "Ticamība",
    person: "Persona",
  };
  function renderMobileFilterState() {
    const chipsEl = document.querySelector(".pzv1-mobile-chips");
    const countEl = document.querySelector(".pzv1-mobile-count");
    if (!chipsEl || !countEl) return;

    const actives = [];
    // Single-select axes: topic, party, period, confidence
    document.querySelectorAll('.pzv1-rail-row[data-axis].is-active').forEach(btn => {
      const axis = btn.dataset.axis;
      const value = btn.dataset.value;
      if (axis === "person") return; // person handled below as multi-select
      if (DEFAULT_VALUES[axis] === value) return;
      const label = btn.querySelector(".pzv1-rail-label")?.textContent?.trim() || value;
      actives.push({ axis, value, label });
    });
    // Multi-select axis: person
    document.querySelectorAll('.pzv1-rail-person.is-active').forEach(btn => {
      const value = btn.dataset.value;
      const label = btn.querySelector(".pzv1-rail-label")?.textContent?.trim() || value;
      actives.push({ axis: "person", value, label });
    });

    countEl.textContent = `(${actives.length})`;

    // Rebuild chip bar
    chipsEl.innerHTML = "";
    for (const a of actives) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "pzv1-chip";
      chip.dataset.axis = a.axis;
      chip.dataset.value = a.value;
      chip.setAttribute("aria-label", `Noņemt filtru: ${AXIS_LABELS[a.axis]}: ${a.label}`);
      chip.innerHTML = `<span class="pzv1-chip-label">${AXIS_LABELS[a.axis]}: ${a.label}</span><span class="pzv1-chip-x" aria-hidden="true">✕</span>`;
      chipsEl.appendChild(chip);
    }
    if (actives.length >= 2) {
      const clearBtn = document.createElement("button");
      clearBtn.type = "button";
      clearBtn.className = "pzv1-mobile-clearall";
      clearBtn.textContent = "Notīrīt visu";
      chipsEl.appendChild(clearBtn);
    }
    chipsEl.hidden = actives.length === 0;
  }

  // --- Filtering ---
  function periodCutoff(period) {
    if (period === "visi") return null;
    const now = new Date();
    if (period === "nedela") {
      const d = new Date(now); d.setDate(d.getDate() - 7);
      return d.toISOString().slice(0, 10);
    }
    if (period === "menesis") {
      return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
    }
    if (period === "gads") {
      return `${now.getFullYear()}-01-01`;
    }
    return null;
  }

  function matchesExcept(c, skipAxis) {
    if (skipAxis !== "topic") {
      if (pzState.topic !== "visas" && c[IDX_TOPIC] !== pzState.topic) return false;
    }
    if (skipAxis !== "party") {
      if (pzState.party !== "Visas") {
        if (pzState.party === "Bez partijas") {
          if (c[IDX_PARTY]) return false;
        } else {
          if (c[IDX_PARTY] !== pzState.party) return false;
        }
      }
    }
    if (skipAxis !== "person") {
      if (pzState.persons.size > 0 && !pzState.persons.has(c[IDX_PERSON])) return false;
    }
    if (skipAxis !== "period") {
      const cutoff = periodCutoff(pzState.period);
      if (cutoff && c[IDX_DATE] < cutoff) return false;
    }
    if (skipAxis !== "confidence") {
      if (pzState.confidence === "augsta" && c[IDX_CONF_TIER] !== "augsta") return false;
      if (pzState.confidence === "laba"
          && c[IDX_CONF_TIER] !== "augsta" && c[IDX_CONF_TIER] !== "laba") return false;
    }
    if (skipAxis !== "query") {
      if (pzState.query) {
        // Smart search: katram vaicājuma vārdam (folded, bez interpunkcijas
        // prasībām) jābūt haystack'ā — secība un komati nav svarīgi.
        // Tokeni memoizēti — matchesExcept izsauc ~1M reižu per keystroke
        // (updateFacetedCounts: ~200 pogas × 4.6k rindas); fold+split šeit
        // inline 2026-07-22 uzkāra lapu.
        const tokens = queryTokens();
        const hay = rowHay(c);
        for (let i = 0; i < tokens.length; i++) {
          if (hay.indexOf(tokens[i]) === -1) return false;
        }
      }
    }
    return true;
  }

  function filterAndSort() {
    const filtered = data.filter(c => matchesExcept(c, null));
    const s = pzState.sort;
    if (s === "date") {
      filtered.sort((a, b) => (b[IDX_DATE] || "").localeCompare(a[IDX_DATE] || ""));
    } else if (s === "confidence") {
      filtered.sort((a, b) => (b[IDX_CONF] || 0) - (a[IDX_CONF] || 0));
    } else if (s === "topic") {
      filtered.sort((a, b) => (a[IDX_TOPIC] || "").localeCompare(b[IDX_TOPIC] || ""));
    }
    return filtered;
  }

  function renderRows(filtered) {
    const page = pzState.page;
    const slice = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
    if (slice.length === 0) {
      rowsEl.innerHTML = '<div class="pzv1-empty">Nav atbilstošu pozīciju.</div>';
      return;
    }
    const frag = document.createDocumentFragment();
    for (const c of slice) {
      frag.appendChild(renderRow(c));
    }
    rowsEl.innerHTML = "";
    rowsEl.appendChild(frag);
  }

  function renderRow(c) {
    const row = document.createElement("div");
    row.className = "pzv1-row";
    row.style.borderLeftColor = "transparent";
    row.addEventListener("mouseenter", () => { row.style.borderLeftColor = c[IDX_PARTY_COLOR]; });
    row.addEventListener("mouseleave", () => { row.style.borderLeftColor = "transparent"; });

    const topicColor = topicColorFor(c[IDX_TOPIC]);
    const topicColorStyle = topicColor ? ` style="--topic-color:${esc(topicColor)}"` : "";
    const dots = [0, 1, 2].map(i => {
      const on = (c[IDX_CONF_TIER] === "augsta" && i < 3)
             || (c[IDX_CONF_TIER] === "laba"   && i < 2)
             || (c[IDX_CONF_TIER] === "merena" && i < 1);
      return `<span class="pzv1-conf-dot${on ? " is-on" : ""}"></span>`;
    }).join("");
    const tierLabel = { augsta: "Augsta", laba: "Laba", merena: "Mērena" }[c[IDX_CONF_TIER]] || "";

    row.innerHTML =
      `<div>
         <div class="pzv1-row-persona-name"><a href="politiki/${esc(c[IDX_SLUG])}.html">${esc(c[IDX_PERSON])}</a></div>
         <div class="pzv1-row-party" style="--party-color:${esc(c[IDX_PARTY_COLOR])}">${esc(c[IDX_PARTY_SHORT])}</div>
       </div>
       <div>
         <button type="button" class="pzv1-row-topic-chip"${topicColorStyle} data-topic="${esc(c[IDX_TOPIC])}">${esc(c[IDX_TOPIC])}</button>
       </div>
       <div><p class="pzv1-row-text">${esc(c[IDX_STANCE])}</p></div>
       <div class="pzv1-row-date">${esc(c[IDX_DATE])}</div>
       <div class="pzv1-row-confidence">
         <span class="pzv1-conf-line" title="Ticamība ${Number(c[IDX_CONF]).toFixed(2)}">
           <span class="pzv1-conf-dots">${dots}</span>
           <span class="pzv1-conf-label">${esc(tierLabel)}</span>
         </span>
         ${c[IDX_SOURCE_URL]
           ? `<a class="pzv1-row-source" href="${esc(c[IDX_SOURCE_URL])}" target="_blank" rel="noopener">${esc(c[IDX_SOURCE_DOMAIN] || "avots")} ↗</a>`
           : ""}
       </div>`;
    return row;
  }

  function renderPagination(total) {
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (pages === 1) { paginationEl.innerHTML = ""; return; }
    const p = pzState.page;
    const nums = paginationNumbers(p, pages);
    const numsHtml = nums.map(n => n === "…"
      ? '<span class="pzv1-pagination-ellipsis">…</span>'
      : `<button type="button" class="${n === p ? "is-active" : ""}" data-page="${n}">${n}</button>`
    ).join("");
    paginationEl.innerHTML =
      `<button type="button" data-page="${p - 1}" ${p <= 1 ? "disabled" : ""}>← prev</button>
       <div class="pzv1-pagination-pages">${numsHtml}</div>
       <button type="button" data-page="${p + 1}" ${p >= pages ? "disabled" : ""}>next →</button>`;
  }

  function paginationNumbers(current, total) {
    // Always show: 1, last, current±1. Ellipsis elsewhere.
    const set = new Set([1, total, current, current - 1, current + 1]);
    const nums = [...set].filter(n => n >= 1 && n <= total).sort((a, b) => a - b);
    const out = [];
    for (let i = 0; i < nums.length; i++) {
      if (i > 0 && nums[i] - nums[i - 1] > 1) out.push("…");
      out.push(nums[i]);
    }
    return out;
  }

  function renderShownCount(total) {
    if (shownEl) shownEl.textContent = total;
  }

  function renderActiveClear() {
    const active = pzState.topic !== "visas"
                || pzState.party !== "Visas"
                || pzState.persons.size > 0
                || pzState.period !== "visi"
                || pzState.confidence !== "visas"
                || pzState.query !== "";
    if (clearEl) clearEl.hidden = !active;
  }

  function updateFacetedCounts() {
    // For each axis, each rail row shows how many rows match if we TOGGLE that value on this axis
    // while keeping every other axis at its current state.
    //
    // Pārrakstīts 2026-07-22: iepriekš katra poga filtrēja VISU data masīvu
    // (~200 pogas × 4.6k rindas ≈ 1M matchesExcept per keystroke) — ar smart
    // search fold to uzkāra lapu. Tagad topic/party/person asīm viens
    // caurskrējiens savāc count kartes; period/confidence (pa ~4 vērtībām)
    // paliek pa filtram uz vērtību.
    const topicCounts = Object.create(null);
    const partyCounts = Object.create(null);
    const personCounts = Object.create(null);
    let topicBase = 0, partyBase = 0, partyNone = 0;
    for (let i = 0; i < data.length; i++) {
      const c = data[i];
      if (matchesExcept(c, "topic")) {
        topicBase++;
        topicCounts[c[IDX_TOPIC]] = (topicCounts[c[IDX_TOPIC]] || 0) + 1;
      }
      if (matchesExcept(c, "party")) {
        partyBase++;
        if (!c[IDX_PARTY]) partyNone++;
        else partyCounts[c[IDX_PARTY]] = (partyCounts[c[IDX_PARTY]] || 0) + 1;
      }
      if (matchesExcept(c, "person")) {
        personCounts[c[IDX_PERSON]] = (personCounts[c[IDX_PERSON]] || 0) + 1;
      }
    }
    const axisCounts = { period: Object.create(null), confidence: Object.create(null) };
    document.querySelectorAll(".pzv1-rail-row[data-axis]").forEach(btn => {
      const axis = btn.dataset.axis;
      const value = btn.dataset.value;
      let count;
      if (axis === "topic") {
        count = value === "visas" ? topicBase : (topicCounts[value] || 0);
      } else if (axis === "party") {
        if (value === "Visas") count = partyBase;
        else if (value === "Bez partijas") count = partyNone;
        else count = partyCounts[value] || 0;
      } else if (axis === "person") {
        count = personCounts[value] || 0;
      } else if (axis === "period" || axis === "confidence") {
        if (axisCounts[axis][value] === undefined) {
          const save = pzState[axis];
          pzState[axis] = value;
          axisCounts[axis][value] = data.filter(c => matchesExcept(c, null)).length;
          pzState[axis] = save;
        }
        count = axisCounts[axis][value];
      } else {
        return;
      }
      const countEl = btn.querySelector(".pzv1-rail-count");
      if (countEl) countEl.textContent = count;
    });
  }

  // --- Clear button ---
  if (clearEl) {
    clearEl.addEventListener("click", () => {
      pzState.topic = "visas";
      pzState.party = "Visas";
      pzState.persons.clear();
      pzState.period = "visi";
      pzState.confidence = "visas";
      pzState.query = "";
      pzState.page = 1;
      if (searchEl) searchEl.value = "";
      document.querySelectorAll(".pzv1-rail-row").forEach(b => {
        const axis = b.dataset.axis;
        const isDefault = (axis === "topic" && b.dataset.value === "visas")
                       || (axis === "party" && b.dataset.value === "Visas")
                       || (axis === "period" && b.dataset.value === "visi")
                       || (axis === "confidence" && b.dataset.value === "visas");
        b.classList.toggle("is-active", !!isDefault);
        b.style.borderLeftColor = "";
      });
      document.querySelectorAll(".pzv1-rail-person.is-active").forEach(b => b.classList.remove("is-active"));
      render();
    });
  }

  // --- URL param starts ---
  (function applyUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const persona = params.get("persona");
    if (persona) {
      const name = decodeURIComponent(persona);
      pzState.persons.add(name);
      const btn = document.querySelector(`.pzv1-rail-person[data-value="${CSS.escape(name)}"]`);
      if (btn) btn.classList.add("is-active");
      const details = document.getElementById("pzv1-rail-persons");
      if (details) details.open = true;
    }
    const tema = params.get("tema");
    if (tema) {
      const name = decodeURIComponent(tema);
      pzState.topic = name;
      document.querySelectorAll('.pzv1-rail-row[data-axis="topic"]').forEach(b => {
        b.classList.toggle("is-active", b.dataset.value === name);
        if (b.dataset.value === name && b.dataset.color) b.style.borderLeftColor = b.dataset.color;
      });
      // If the topic is in the hidden tail, expand the extras inline.
      // We can't .click() the expander here because its listener is
      // registered later in the IIFE.
      const hiddenMatch = document.querySelector(`#pzv1-rail-topics .pzv1-rail-hidden .pzv1-rail-row[data-value="${CSS.escape(name)}"]`);
      if (hiddenMatch) {
        const hiddenWrap = hiddenMatch.closest(".pzv1-rail-hidden");
        if (hiddenWrap) hiddenWrap.removeAttribute("hidden");
        const more = document.getElementById("pzv1-topic-more");
        if (more) more.remove();
      }
    }
    const partija = params.get("partija");
    if (partija) {
      const name = decodeURIComponent(partija);
      pzState.party = name;
      document.querySelectorAll('.pzv1-rail-row[data-axis="party"]').forEach(b => {
        b.classList.toggle("is-active", b.dataset.value === name);
        if (b.dataset.value === name && b.dataset.color) b.style.borderLeftColor = b.dataset.color;
      });
    }
    // ?q= — the homepage hero search submits here. URLSearchParams.get
    // already percent/plus-decodes, so no decodeURIComponent.
    const q = params.get("q");
    if (q && q.trim()) {
      pzState.query = q.trim();
      if (searchEl) searchEl.value = pzState.query;
    }
  })();

  // --- Keyboard ---
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".pzv1-rail-details[open]").forEach(d => { d.open = false; });
    } else if (e.key === "/" && document.activeElement !== searchEl
               && !(document.activeElement && document.activeElement.tagName === "INPUT")) {
      e.preventDefault();
      if (searchEl) searchEl.focus();
    }
  });

  // --- Pagination click ---
  paginationEl.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-page]");
    if (!btn || btn.disabled) return;
    const n = parseInt(btn.dataset.page, 10);
    if (Number.isFinite(n) && n >= 1) {
      pzState.page = n;
      render();
      // Scroll to top of table so the new page is in view
      const main = document.querySelector(".pzv1-main");
      if (main) main.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });

  // --- Row topic chip → set topic filter ---
  rowsEl.addEventListener("click", (e) => {
    const chip = e.target.closest(".pzv1-row-topic-chip");
    if (!chip) return;
    e.stopPropagation();
    const topic = chip.dataset.topic;
    const railBtn = document.querySelector(`.pzv1-rail-row[data-axis="topic"][data-value="${CSS.escape(topic)}"]`);
    if (railBtn) railBtn.click();
  });

  // --- Rail: single-select axes ---
  function railSingleSelect(axis, resetValue) {
    document.querySelectorAll(`.pzv1-rail-row[data-axis="${axis}"]`).forEach(btn => {
      btn.addEventListener("click", () => {
        const currentActive = document.querySelector(`.pzv1-rail-row[data-axis="${axis}"].is-active`);
        const wasActive = btn === currentActive;
        document.querySelectorAll(`.pzv1-rail-row[data-axis="${axis}"]`).forEach(b => {
          b.classList.remove("is-active");
          b.style.borderLeftColor = "";
        });
        let newValue;
        if (wasActive && btn.dataset.value !== resetValue) {
          // toggle off → go to default
          const def = document.querySelector(`.pzv1-rail-row[data-axis="${axis}"][data-value="${CSS.escape(resetValue)}"]`);
          if (def) def.classList.add("is-active");
          newValue = resetValue;
        } else {
          btn.classList.add("is-active");
          if (btn.dataset.color) btn.style.borderLeftColor = btn.dataset.color;
          newValue = btn.dataset.value;
        }
        pzState[axis] = newValue;
        pzState.page = 1;
        render();
      });
    });
  }
  railSingleSelect("topic", "visas");
  railSingleSelect("party", "Visas");
  railSingleSelect("period", "visi");
  railSingleSelect("confidence", "visas");

  // --- Rail: persons (multi-select) ---
  document.querySelectorAll('.pzv1-rail-row[data-axis="person"]').forEach(btn => {
    btn.addEventListener("click", () => {
      const name = btn.dataset.value;
      if (pzState.persons.has(name)) {
        pzState.persons.delete(name);
        btn.classList.remove("is-active");
      } else {
        pzState.persons.add(name);
        btn.classList.add("is-active");
      }
      pzState.page = 1;
      render();
    });
  });

  const personSearchEl = document.querySelector("#pzv1-rail-persons .pzv1-rail-search-input");
  if (personSearchEl) {
    personSearchEl.addEventListener("input", () => {
      const q = personSearchEl.value.trim().toLowerCase();
      document.querySelectorAll(".pzv1-rail-person").forEach(btn => {
        const label = btn.querySelector(".pzv1-rail-label").textContent.toLowerCase();
        btn.classList.toggle("is-hidden", q && !label.includes(q));
      });
    });
  }

  // --- Rail: topic "+ rādīt visas 26" expander ---
  // NOTE: hidden rows already have their single-select listener attached
  // by railSingleSelect("topic", ...) above, since querySelectorAll iterates
  // regardless of the parent's `hidden` attribute. We only need to unhide.
  const topicMoreBtn = document.getElementById("pzv1-topic-more");
  if (topicMoreBtn) {
    topicMoreBtn.addEventListener("click", () => {
      const hidden = topicMoreBtn.nextElementSibling;
      if (!hidden || !hidden.classList.contains("pzv1-rail-hidden")) return;
      hidden.removeAttribute("hidden");
      topicMoreBtn.remove();
    });
  }

  // --- Search input ---
  if (searchEl) {
    // Debounce: pilnais render (filtrs + faceted counts) tikai pēc rakstīšanas
    // pauzes, ne uz katru taustiņsitienu.
    let searchTimer = null;
    searchEl.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        pzState.query = searchEl.value.trim();
        pzState.page = 1;
        render();
      }, 150);
    });
  }

  // --- Sort buttons ---
  document.querySelectorAll(".pzv1-sortbtn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".pzv1-sortbtn").forEach(b => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      pzState.sort = btn.dataset.sort;
      pzState.page = 1;
      render();
    });
  });

  // --- Mobile filter toggle ---
  const mobileToggleEl = document.querySelector(".pzv1-mobile-toggle");
  const mobileGridEl = document.querySelector(".pzv1-grid");
  if (mobileToggleEl && mobileGridEl) {
    mobileToggleEl.addEventListener("click", () => {
      const isOpen = mobileGridEl.dataset.mobileFilterOpen === "true";
      mobileGridEl.dataset.mobileFilterOpen = String(!isOpen);
      mobileToggleEl.setAttribute("aria-expanded", String(!isOpen));
    });
  }

  // --- Mobile chip clicks ---
  const mobileChipsEl = document.querySelector(".pzv1-mobile-chips");
  if (mobileChipsEl) {
    mobileChipsEl.addEventListener("click", (e) => {
      // "Notīrīt visu"
      const clearAll = e.target.closest(".pzv1-mobile-clearall");
      if (clearAll) {
        const mainClear = document.getElementById("pzv1-clear");
        if (mainClear) mainClear.click();
        return;
      }
      // Individual chip: simulate click on the corresponding rail row
      // to remove this one filter via existing code paths.
      const chip = e.target.closest(".pzv1-chip");
      if (!chip) return;
      const axis = chip.dataset.axis;
      const value = chip.dataset.value;
      if (axis === "person") {
        // Multi-select: clicking the active row toggles it off.
        const btn = document.querySelector(
          `.pzv1-rail-person[data-value="${CSS.escape(value)}"]`
        );
        if (btn) btn.click();
      } else {
        // Single-select: click the active row to toggle off → goes to default.
        const active = document.querySelector(
          `.pzv1-rail-row[data-axis="${axis}"].is-active`
        );
        if (active) active.click();
      }
    });
  }

  // --- Bootstrap ---
  // All event-listener blocks from later tasks (4.2–4.5) must be inserted
  // ABOVE this Bootstrap section, inside the same IIFE.
  function showLoading(msg) {
    if (rowsEl) rowsEl.innerHTML = `<div class="pzv1-empty">${esc(msg)}</div>`;
  }

  async function initData() {
    if (Array.isArray(window._pzData)) {
      data = window._pzData;
      window._pzData = null;
      render();
      return;
    }
    showLoading("Ielādē pozīcijas…");
    try {
      const resp = await fetch("pozicijas-data.json", { cache: "default" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      data = await resp.json();
      render();
    } catch (e) {
      showLoading("Neizdevās ielādēt pozīcijas. Mēģini pārlādēt lapu.");
      console.error("pzv1: data fetch failed —", e);
    }
  }

  initData();
})();
