// X tab V1 — filter + interaction logic.
// Runs on /x.html. Handles: ticker tab (type), persona multi-select,
// partija multi-select, topic chip filter (from aside click or URL param).

(function () {
  "use strict";

  // --- State ---
  const state = {
    type: "",                // "" | "post" | "mention"
    personas: new Set(),     // Set<string>
    parties: new Set(),      // Set<string>
    topic: null,             // string | null
  };

  const feed = document.getElementById("xv1-feed");
  if (!feed) return;
  const items = Array.from(feed.querySelectorAll(".xv1-item"));

  // --- Apply filters ---
  function apply() {
    for (const el of items) {
      const t = el.dataset.type;
      const p = el.dataset.persona;
      const party = el.dataset.party;
      const topic = el.dataset.topic;
      const matchType    = !state.type || t === state.type;
      const matchPersona = state.personas.size === 0 || state.personas.has(p);
      const matchParty   = state.parties.size === 0 || state.parties.has(party);
      const matchTopic   = !state.topic || topic === state.topic;
      el.style.display = (matchType && matchPersona && matchParty && matchTopic) ? "" : "none";
    }
  }

  // --- Ticker tabs (type) ---
  document.querySelectorAll(".xv1-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".xv1-tab").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.type = btn.dataset.type || "";
      apply();
    });
  });

  // --- Multi-select dropdowns ---
  function setupMultiSelect(rootId, targetSet, singularLabel, pluralLabel) {
    const root = document.getElementById(rootId);
    if (!root) return null;
    const trigger = root.querySelector(".xv1-select-trigger");
    const label = root.querySelector(".xv1-select-label");
    const options = root.querySelectorAll(".xv1-select-option");
    const clear = root.querySelector(".xv1-select-clear");

    trigger.addEventListener("click", e => {
      e.stopPropagation();
      document.querySelectorAll(".xv1-select.open").forEach(s => {
        if (s !== root) s.classList.remove("open");
      });
      root.classList.toggle("open");
    });
    options.forEach(opt => {
      opt.addEventListener("click", e => {
        e.stopPropagation();
        const v = opt.dataset.value;
        if (targetSet.has(v)) { targetSet.delete(v); opt.classList.remove("selected"); }
        else { targetSet.add(v); opt.classList.add("selected"); }
        updateLabel();
        apply();
      });
    });
    clear.addEventListener("click", e => {
      e.stopPropagation();
      targetSet.clear();
      options.forEach(o => o.classList.remove("selected"));
      updateLabel();
      apply();
    });

    function updateLabel() {
      if (targetSet.size === 0) {
        label.textContent = singularLabel;
        root.classList.remove("has-selection");
      } else if (targetSet.size === 1) {
        label.textContent = Array.from(targetSet)[0];
        root.classList.add("has-selection");
      } else {
        label.textContent = `${targetSet.size} ${pluralLabel}`;
        root.classList.add("has-selection");
      }
    }
    return { updateLabel, options };
  }

  const personaCtl = setupMultiSelect("xv1-persona-select", state.personas, "Visas personas", "personas");
  const partyCtl   = setupMultiSelect("xv1-party-select",   state.parties,   "Visas partijas", "partijas");

  document.addEventListener("click", e => {
    document.querySelectorAll(".xv1-select.open").forEach(s => {
      if (!s.contains(e.target)) s.classList.remove("open");
    });
  });

  // --- Topic chip (from aside click or URL) ---
  const topicHolder = document.getElementById("xv1-topic-chip");
  function setTopic(topic) {
    state.topic = topic || null;
    topicHolder.innerHTML = "";
    if (topic) {
      const chip = document.createElement("span");
      chip.className = "xv1-topic-chip";
      chip.innerHTML = `<span>${topic}</span><button type="button" aria-label="Noņemt tēmas filtru">×</button>`;
      chip.querySelector("button").addEventListener("click", () => setTopic(null));
      topicHolder.appendChild(chip);
    }
    apply();
  }

  document.querySelectorAll(".xv1-topic-row").forEach(row => {
    row.addEventListener("click", () => setTopic(row.dataset.topic));
  });
  // Single-select semantics: click replaces current filter with this one.
  // Clicking the same value again clears it (toggle-off).
  function selectSingle(targetSet, value, dropdownId, ctl) {
    const isAlreadySole = targetSet.size === 1 && targetSet.has(value);
    targetSet.clear();
    document.querySelectorAll(`#${dropdownId} .xv1-select-option.selected`)
      .forEach(o => o.classList.remove("selected"));
    if (!isAlreadySole) {
      targetSet.add(value);
      const opt = document.querySelector(`#${dropdownId} .xv1-select-option[data-value="${CSS.escape(value)}"]`);
      if (opt) opt.classList.add("selected");
    }
    if (ctl) ctl.updateLabel();
    apply();
  }
  const selectSinglePersona = (name) =>
    selectSingle(state.personas, name, "xv1-persona-select", personaCtl);
  const selectSingleParty = (party) =>
    selectSingle(state.parties, party, "xv1-party-select", partyCtl);

  document.querySelectorAll(".xv1-mention-row").forEach(row => {
    row.addEventListener("click", () => selectSinglePersona(row.dataset.persona));
  });
  // Inline @handle buttons in ticker items — click to filter by persona.
  document.querySelectorAll(".xv1-item-at").forEach(btn => {
    btn.addEventListener("click", e => {
      e.stopPropagation();
      selectSinglePersona(btn.dataset.persona);
    });
  });
  // Inline party short-code buttons in ticker items — click to filter by party.
  document.querySelectorAll(".xv1-item-party").forEach(btn => {
    btn.addEventListener("click", e => {
      e.stopPropagation();
      selectSingleParty(btn.dataset.party);
    });
  });
  // Inline topic chips in ticker items — click to filter by topic (toggle).
  document.querySelectorAll(".xv1-item-topic").forEach(btn => {
    btn.addEventListener("click", e => {
      e.stopPropagation();
      const topic = btn.dataset.topic;
      setTopic(state.topic === topic ? null : topic);
    });
  });

  // --- URL params ---
  const params = new URLSearchParams(location.search);
  const pPersona = params.get("persona");
  if (pPersona) {
    const val = decodeURIComponent(pPersona);
    state.personas.add(val);
    const opt = document.querySelector(`#xv1-persona-select .xv1-select-option[data-value="${CSS.escape(val)}"]`);
    if (opt) opt.classList.add("selected");
    if (personaCtl) personaCtl.updateLabel();
  }
  const pParty = params.get("partija");
  if (pParty) {
    const val = decodeURIComponent(pParty);
    state.parties.add(val);
    const opt = document.querySelector(`#xv1-party-select .xv1-select-option[data-value="${CSS.escape(val)}"]`);
    if (opt) opt.classList.add("selected");
    if (partyCtl) partyCtl.updateLabel();
  }
  const pType = params.get("tips");
  if (pType === "post" || pType === "mention") {
    const btn = document.querySelector(`.xv1-tab[data-type="${pType}"]`);
    if (btn) btn.click();
  }
  const pTopic = params.get("tema");
  if (pTopic) setTopic(decodeURIComponent(pTopic));

  apply();

  // --- Search filter inside persona dropdown ---
  window.xv1FilterOptions = function (input) {
    const q = input.value.toLowerCase();
    const dropdown = input.closest(".xv1-select-dropdown");
    dropdown.querySelectorAll(".xv1-select-option").forEach(opt => {
      opt.style.display = (!q || opt.textContent.toLowerCase().includes(q)) ? "" : "none";
    });
  };
})();
