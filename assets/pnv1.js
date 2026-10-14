// Personas V1 — rail filter + sort for /personas.html.
// Cards are server-rendered; this script toggles display and reorders DOM.
//
// State axes (all single-value except party which is multi):
//   category: "visas" | <category name>
//   party:    Set<string>   (empty === all)
//   coalition: "visas" | "coalition" | "opposition" | "other"
//   saeima15: "visi" | "ieveleti" | "jauni"  (card data-saeima15: "jauns" | "ievēlēts" | "")
//   query:    string (lowercased)
//   sort:     "alfabets" | "aktivitate" | "pretrunas" | "pozicijas"

(function () {
  "use strict";

  const state = {
    category: "visas",
    party: new Set(),
    coalition: "visas",
    // Noklusējums «Ievēlētie» (operatora lūgums 2026-10-05): lapa atveras ar 15. Saeimas
    // ievēlētajiem; «Notīrīt visu» un čipa noņemšana atgriež «visi». Veidnē is-active jāsakrīt.
    saeima15: "ieveleti",
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

  // Viens predikāts gan sarakstam, gan raila skaitļiem — tie nevar atšķirties.
  // `st` ir state forma (category/party/coalition/saeima15/query).
  function matchesState(card, st) {
    const d = card.dataset;
    if (st.category !== "visas" && d.category !== st.category) return false;
    if (st.party.size > 0 && !st.party.has(d.party)) return false;
    if (st.coalition !== "visas" && d.coalition !== st.coalition) return false;
    // Jauns profils ir arī ievēlēts — "ieveleti" ietver abus.
    if (st.saeima15 === "ieveleti" && !d.saeima15) return false;
    if (st.saeima15 === "jauni" && d.saeima15 !== "jauns") return false;
    if (st.query) {
      const hay = d.name + " " + d.role + " " + d.party.toLowerCase() + " " + d.partyShort.toLowerCase();
      if (!hay.includes(st.query)) return false;
    }
    return true;
  }
  const cardMatches = card => matchesState(card, state);

  // Fasetes skaitļi: katrai raila rindai — kartītes, kas atbilst VISĀM pārējām asīm
  // (arī meklēšanai) plus šīs rindas vērtībai. Savas ass izvēle netiek ņemta vērā;
  // partijai (multi) rindas skaitlis neņem vērā pašreizējo partiju izvēli.
  const railAxes = [
    { id: "pnv1-rail-saeima15", axis: "saeima15" },
    { id: "pnv1-rail-categories", axis: "category" },
    { id: "pnv1-rail-parties", axis: "party" },
    { id: "pnv1-rail-coalition", axis: "coalition" },
  ];
  function updateFacetCounts() {
    for (const { id, axis } of railAxes) {
      const group = document.getElementById(id);
      if (!group) continue;
      group.querySelectorAll(".pnv1-rail-row").forEach(btn => {
        const countEl = btn.querySelector(".pnv1-rail-count");
        if (!countEl) return;
        const v = btn.dataset.value;
        const st = Object.assign({}, state);
        st.party = axis === "party" ? new Set(v === "Visas" ? [] : [v]) : state.party;
        if (axis !== "party") st[axis] = v;
        let n = 0;
        for (const card of cards) if (matchesState(card, st)) n += 1;
        countEl.textContent = String(n);
      });
    }
  }

  // Alfabēts kārto pēc UZVĀRDA — renderer ieliek data-sort-name
  // ("Viļums Juris"); organizācijām (Mediji/Iestādes) tas sakrīt ar vārdu.
  const sortName = c => c.dataset.sortName || c.dataset.name;

  function compareCards(a, b) {
    const da = a.dataset, db = b.dataset;
    switch (state.sort) {
      case "aktivitate":
        // Descending: newest first. Empty string sorts last.
        return (db.lastIso || "").localeCompare(da.lastIso || "");
      case "pretrunas":
        return parseInt(db.contradictions, 10) - parseInt(da.contradictions, 10)
            || sortName(a).localeCompare(sortName(b));
      case "pozicijas":
        return parseInt(db.positions, 10) - parseInt(da.positions, 10)
            || sortName(a).localeCompare(sortName(b));
      case "alfabets":
      default:
        return sortName(a).localeCompare(sortName(b));
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
    updateFacetCounts();
  };

  // Filtra poga: vizuālā klase un aria-pressed mainās kopā (ekrāna lasītājiem).
  function setActive(btn, on) {
    btn.classList.toggle("is-active", on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  }

  // ── Filter rail rows (category / coalition are single-value; party is multi) ──
  function wireSingleAxis(groupId, axisKey) {
    const container = document.getElementById(groupId);
    if (!container) return;
    container.querySelectorAll(".pnv1-rail-row").forEach(btn => {
      btn.addEventListener("click", () => {
        container.querySelectorAll(".pnv1-rail-row").forEach(b => setActive(b, b === btn));
        state[axisKey] = btn.dataset.value;
        render();
      });
    });
  }
  wireSingleAxis("pnv1-rail-categories", "category");
  wireSingleAxis("pnv1-rail-coalition", "coalition");
  wireSingleAxis("pnv1-rail-saeima15", "saeima15");

  // Party is multi-select: clicking "Visas partijas" clears, others toggle
  const partyGroup = document.getElementById("pnv1-rail-parties");
  if (partyGroup) {
    partyGroup.querySelectorAll(".pnv1-rail-row").forEach(btn => {
      btn.addEventListener("click", () => {
        const val = btn.dataset.value;
        if (val === "Visas") {
          state.party.clear();
          partyGroup.querySelectorAll(".pnv1-rail-row").forEach(b => setActive(b, b === btn));
        } else {
          setActive(partyGroup.querySelector('[data-value="Visas"]'), false);
          if (state.party.has(val)) {
            state.party.delete(val);
            setActive(btn, false);
          } else {
            state.party.add(val);
            setActive(btn, true);
          }
          if (state.party.size === 0) {
            setActive(partyGroup.querySelector('[data-value="Visas"]'), true);
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
      document.querySelectorAll(".pnv1-sortbtn").forEach(b => setActive(b, b === btn));
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

  // ── Active chips bar (one container for desktop + mobile; mobile toggle shows the count) ──
  const chipsEl = document.getElementById("pnv1-active-chips");
  const mobileCountEl = document.querySelector(".pnv1-mobile-count");

  function renderChips() {
    if (!chipsEl) return;
    const chips = [];
    if (state.category !== "visas") chips.push({ axis: "category", label: state.category });
    state.party.forEach(p => chips.push({ axis: "party", label: p }));
    if (state.coalition !== "visas") {
      const label = { coalition: "Koalīcijā", opposition: "Opozīcijā", other: "Bez Saeimas frakcijas" }[state.coalition] || state.coalition;
      chips.push({ axis: "coalition", label });
    }
    if (state.saeima15 !== "visi") {
      const label = { ieveleti: "15. Saeimā ievēlētie", jauni: "Jaunie 15. Saeimas deputāti" }[state.saeima15] || state.saeima15;
      chips.push({ axis: "saeima15", label });
    }
    if (state.query) chips.push({ axis: "query", label: `"${state.query}"` });

    if (mobileCountEl) mobileCountEl.textContent = `(${chips.length})`;
    chipsEl.hidden = chips.length === 0;
    chipsEl.innerHTML = "";

    for (const { axis, label } of chips) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "pnv1-chip";
      chip.textContent = label + " ✕";
      chip.setAttribute("aria-label", "Noņemt filtru: " + label);
      chip.addEventListener("click", () => {
        if (axis === "category") state.category = "visas";
        else if (axis === "party") state.party.delete(label);
        else if (axis === "coalition") state.coalition = "visas";
        else if (axis === "saeima15") state.saeima15 = "visi";
        else if (axis === "query") {
          state.query = "";
          if (searchEl) searchEl.value = "";
          if (clearEl) clearEl.hidden = true;
        }
        // Reflect in rail UI
        syncRailUI();
        render();
      });
      chipsEl.appendChild(chip);
    }

    if (chips.length > 1) {
      const clearAll = document.createElement("button");
      clearAll.type = "button";
      clearAll.className = "pnv1-clearall";
      clearAll.textContent = "Notīrīt visus";
      clearAll.addEventListener("click", () => {
        state.category = "visas";
        state.party.clear();
        state.coalition = "visas";
        state.saeima15 = "visi";
        state.query = "";
        if (searchEl) searchEl.value = "";
        if (clearEl) clearEl.hidden = true;
        syncRailUI();
        render();
      });
      chipsEl.appendChild(clearAll);
    }
  }

  function syncRailUI() {
    // Category
    document.querySelectorAll("#pnv1-rail-categories .pnv1-rail-row").forEach(b => {
      setActive(b, b.dataset.value === state.category);
    });
    // Coalition
    document.querySelectorAll("#pnv1-rail-coalition .pnv1-rail-row").forEach(b => {
      setActive(b, b.dataset.value === state.coalition);
    });
    // 15. Saeima
    document.querySelectorAll("#pnv1-rail-saeima15 .pnv1-rail-row").forEach(b => {
      setActive(b, b.dataset.value === state.saeima15);
    });
    // Party
    document.querySelectorAll("#pnv1-rail-parties .pnv1-rail-row").forEach(b => {
      const v = b.dataset.value;
      if (v === "Visas") setActive(b, state.party.size === 0);
      else setActive(b, state.party.has(v));
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
