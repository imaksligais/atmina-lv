// Personas V1 — rail filter + sort for /personas.html.
// Cards are server-rendered; this script toggles display and reorders DOM.
//
// State axes (all single-value except party which is multi):
//   category: "visas" | <category name>
//   party:    Set<string>   (empty === all)
//   coalition: "visas" | "coalition" | "opposition" | "other"
//   query:    string (lowercased)
//   sort:     "alfabets" | "aktivitate" | "pretrunas" | "pozicijas"

(function () {
  "use strict";

  const state = {
    category: "visas",
    party: new Set(),
    coalition: "visas",
    query: "",
    sort: "aktivitate",
  };

  const cardsEl = document.getElementById("pnv1-cards");
  const emptyEl = document.getElementById("pnv1-empty");
  const shownEl = document.getElementById("pnv1-shown");
  const searchEl = document.getElementById("pnv1-search");
  const clearEl = document.getElementById("pnv1-clear");
  if (!cardsEl) return;

  const cards = Array.from(cardsEl.querySelectorAll(".pnv1-card"));

  function cardMatches(card) {
    const d = card.dataset;
    if (state.category !== "visas" && d.category !== state.category) return false;
    if (state.party.size > 0 && !state.party.has(d.party)) return false;
    if (state.coalition !== "visas" && d.coalition !== state.coalition) return false;
    if (state.query) {
      const hay = d.name + " " + d.role + " " + d.party.toLowerCase() + " " + d.partyShort.toLowerCase();
      if (!hay.includes(state.query)) return false;
    }
    return true;
  }

  function compareCards(a, b) {
    const da = a.dataset, db = b.dataset;
    switch (state.sort) {
      case "aktivitate":
        // Descending: newest first. Empty string sorts last.
        return (db.lastIso || "").localeCompare(da.lastIso || "");
      case "pretrunas":
        return parseInt(db.contradictions, 10) - parseInt(da.contradictions, 10)
            || da.name.localeCompare(db.name);
      case "pozicijas":
        return parseInt(db.positions, 10) - parseInt(da.positions, 10)
            || da.name.localeCompare(db.name);
      case "alfabets":
      default:
        return da.name.localeCompare(db.name);
    }
  }

  let render = function () {
    let shown = 0;
    const ordered = cards.slice().sort(compareCards);

    // Reorder DOM + toggle display in one pass
    const frag = document.createDocumentFragment();
    for (const card of ordered) {
      if (cardMatches(card)) {
        card.style.display = "";
        shown += 1;
      } else {
        card.style.display = "none";
      }
      frag.appendChild(card);
    }
    cardsEl.appendChild(frag);

    if (shownEl) shownEl.textContent = String(shown);
    if (emptyEl) emptyEl.hidden = shown !== 0;
  };

  // ── Filter rail rows (category / coalition are single-value; party is multi) ──
  function wireSingleAxis(groupId, axisKey) {
    const container = document.getElementById(groupId);
    if (!container) return;
    container.querySelectorAll(".pnv1-rail-row").forEach(btn => {
      btn.addEventListener("click", () => {
        container.querySelectorAll(".pnv1-rail-row").forEach(b => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        state[axisKey] = btn.dataset.value;
        render();
      });
    });
  }
  wireSingleAxis("pnv1-rail-categories", "category");
  wireSingleAxis("pnv1-rail-coalition", "coalition");

  // Party is multi-select: clicking "Visas partijas" clears, others toggle
  const partyGroup = document.getElementById("pnv1-rail-parties");
  if (partyGroup) {
    partyGroup.querySelectorAll(".pnv1-rail-row").forEach(btn => {
      btn.addEventListener("click", () => {
        const val = btn.dataset.value;
        if (val === "Visas") {
          state.party.clear();
          partyGroup.querySelectorAll(".pnv1-rail-row").forEach(b => b.classList.remove("is-active"));
          btn.classList.add("is-active");
        } else {
          partyGroup.querySelector('[data-value="Visas"]').classList.remove("is-active");
          if (state.party.has(val)) {
            state.party.delete(val);
            btn.classList.remove("is-active");
          } else {
            state.party.add(val);
            btn.classList.add("is-active");
          }
          if (state.party.size === 0) {
            partyGroup.querySelector('[data-value="Visas"]').classList.add("is-active");
          }
        }
        render();
      });
    });
  }

  // ── Search ──
  if (searchEl) {
    searchEl.addEventListener("input", () => {
      state.query = searchEl.value.trim().toLowerCase();
      if (clearEl) clearEl.hidden = state.query === "";
      render();
    });
  }
  if (clearEl) {
    clearEl.addEventListener("click", () => {
      if (searchEl) searchEl.value = "";
      state.query = "";
      clearEl.hidden = true;
      render();
    });
  }

  // ── Sort buttons ──
  document.querySelectorAll(".pnv1-sortbtn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".pnv1-sortbtn").forEach(b => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      state.sort = btn.dataset.sort;
      render();
    });
  });

  // ── Mobile filter panel toggle ──
  const gridEl = document.querySelector(".pnv1-grid");
  const mobileToggleEl = document.querySelector(".pnv1-mobile-toggle");
  if (gridEl && mobileToggleEl) {
    mobileToggleEl.addEventListener("click", () => {
      const isOpen = gridEl.dataset.mobileFilterOpen === "true";
      gridEl.dataset.mobileFilterOpen = isOpen ? "false" : "true";
      mobileToggleEl.setAttribute("aria-expanded", String(!isOpen));
    });
  }

  // ── Active chips bar (count + removable chips) ──
  const mobileChipsEl = document.querySelector(".pnv1-mobile-chips");
  const mobileCountEl = document.querySelector(".pnv1-mobile-count");

  function renderChips() {
    if (!mobileChipsEl || !mobileCountEl) return;
    const chips = [];
    if (state.category !== "visas") chips.push({ axis: "category", label: state.category });
    state.party.forEach(p => chips.push({ axis: "party", label: p }));
    if (state.coalition !== "visas") {
      const label = { coalition: "Koalīcijā", opposition: "Opozīcijā", other: "Bez Saeimas frakcijas" }[state.coalition] || state.coalition;
      chips.push({ axis: "coalition", label });
    }
    if (state.query) chips.push({ axis: "query", label: `"${state.query}"` });

    mobileCountEl.textContent = `(${chips.length})`;
    mobileChipsEl.hidden = chips.length === 0;
    mobileChipsEl.innerHTML = "";

    for (const { axis, label } of chips) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "pnv1-mobile-chip";
      chip.textContent = label + " ✕";
      chip.addEventListener("click", () => {
        if (axis === "category") state.category = "visas";
        else if (axis === "party") state.party.delete(label);
        else if (axis === "coalition") state.coalition = "visas";
        else if (axis === "query") {
          state.query = "";
          if (searchEl) searchEl.value = "";
          if (clearEl) clearEl.hidden = true;
        }
        // Reflect in rail UI
        syncRailUI();
        render();
      });
      mobileChipsEl.appendChild(chip);
    }

    if (chips.length > 1) {
      const clearAll = document.createElement("button");
      clearAll.type = "button";
      clearAll.className = "pnv1-mobile-clearall";
      clearAll.textContent = "Notīrīt visus";
      clearAll.addEventListener("click", () => {
        state.category = "visas";
        state.party.clear();
        state.coalition = "visas";
        state.query = "";
        if (searchEl) searchEl.value = "";
        if (clearEl) clearEl.hidden = true;
        syncRailUI();
        render();
      });
      mobileChipsEl.appendChild(clearAll);
    }
  }

  function syncRailUI() {
    // Category
    document.querySelectorAll("#pnv1-rail-categories .pnv1-rail-row").forEach(b => {
      b.classList.toggle("is-active", b.dataset.value === state.category);
    });
    // Coalition
    document.querySelectorAll("#pnv1-rail-coalition .pnv1-rail-row").forEach(b => {
      b.classList.toggle("is-active", b.dataset.value === state.coalition);
    });
    // Party
    document.querySelectorAll("#pnv1-rail-parties .pnv1-rail-row").forEach(b => {
      const v = b.dataset.value;
      if (v === "Visas") b.classList.toggle("is-active", state.party.size === 0);
      else b.classList.toggle("is-active", state.party.has(v));
    });
  }

  // Re-render chips after every state change — patch render()
  const _originalRender = render;
  render = function () {
    _originalRender();
    renderChips();
  };

  // Expose render for the wiring tasks below
  window.__pnv1 = { state, render };
  render();
})();
