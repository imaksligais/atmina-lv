// X tab V1 — filter + interaction logic.
// Runs on /x.html. Handles: ticker tab (type), persona multi-select,
// partija multi-select, topic chip filter (from aside click or URL param).

(function () {
  "use strict";

  // --- State ---
  const state = {
    type: "post",            // "" | "post" | "mention"; noklusējums — tikai ieraksti
    personas: new Set(),     // Set<string>
    parties: new Set(),      // Set<string>
    topic: null,             // string | null
  };

  const feed = document.getElementById("xv1-feed");
  if (!feed) return;
  const items = Array.from(feed.querySelectorAll(".xv1-item"));
  // «Rāda N no M …» + tukšais stāvoklis — kopīgais window.atminaShowCount
  // (assets/sgv1.js). x-v1 ir `defer` (x.html.j2), lai tas izpildās pēc sgv1:
  // apply() tiek saukts jau ielādē (URL filtri).
  const showCount = (shown, countId, emptyId, noun) =>
    window.atminaShowCount(countId, emptyId, shown, items.length, noun);

  // --- Apply filters ---
  function apply() {
    let shown = 0;
    for (const el of items) {
      const t = el.dataset.type;
      const p = el.dataset.persona;
      const party = el.dataset.party;
      const topic = el.dataset.topic;
      const matchType    = !state.type || t === state.type;
      const matchPersona = state.personas.size === 0 || state.personas.has(p);
      const matchParty   = state.parties.size === 0 || state.parties.has(party);
      const matchTopic   = !state.topic || topic === state.topic;
      const match = matchType && matchPersona && matchParty && matchTopic;
      el.style.display = match ? "" : "none";
      if (match) shown++;
    }
    showCount(shown, "xv1-count", "xv1-empty", "jaunākajiem ierakstiem un pieminējumiem");
  }

  // --- Ticker tabs (type) ---
  // Nav cilnes (role=tab): visas trīs filtrē VIENU plūsmu, tāpēc tās ir
  // filtra pogas ar aria-pressed kā pārējie vietnes filtri.
  // Jebkura filtra maiņa (persona, partija, tēma) atgriež noklusējuma pogu
  // «Tikai ieraksti»; URL parametru ielādes laikā ne — tur `tips` ir noteicējs.
  let booting = true;
  function markType(type) {
    document.querySelectorAll(".xv1-tab").forEach(b => {
      const on = (b.dataset.type || "") === type;
      b.classList.toggle("active", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    state.type = type;
  }
  function resetType() {
    if (booting || state.type === "post") return;
    markType("post");
  }
  document.querySelectorAll(".xv1-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      markType(btn.dataset.type || "");
      apply();
    });
  });

  // --- Multi-select dropdowns ---
  // Kopīgais nolaižamais saraksts (assets/msv1.js); etiķetē pa vārdam tikai 1 vērtība.
  function onSelectChange() { resetType(); apply(); }
  const personaCtl = atminaMultiSelect({ root: "xv1-persona-select", family: "xv1-select",
    selected: state.personas, allLabel: "Visas personas", pluralLabel: "personas",
    maxNamed: 1, onChange: onSelectChange });
  const partyCtl = atminaMultiSelect({ root: "xv1-party-select", family: "xv1-select",
    selected: state.parties, allLabel: "Visas partijas", pluralLabel: "partijas",
    maxNamed: 1, onChange: onSelectChange });

  // --- Topic chip (from aside click or URL) ---
  const topicHolder = document.getElementById("xv1-topic-chip");
  function setTopic(topic) {
    resetType();
    state.topic = topic || null;
    topicHolder.innerHTML = "";
    if (topic) {
      // Noņemams čips (.chip--removable, style.css «Pamatelementi»). Teksts ar
      // textContent — tēma var nākt no ?tema= adresē.
      const chip = document.createElement("span");
      chip.className = "chip chip--removable active xv1-topic-chip";
      const label = document.createElement("span");
      label.textContent = topic;
      const x = document.createElement("button");
      x.type = "button";
      x.className = "chip-x";
      x.setAttribute("aria-label", "Noņemt tēmas filtru");
      x.textContent = "×";
      x.addEventListener("click", () => setTopic(null));
      chip.append(label, x);
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
    resetType();
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

  // «Pieminētākie» — arī šeit sāk ar «Tikai ieraksti» (operatora lēmums 2026-10-08).
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
  if (pType === "visi" || pType === "post" || pType === "mention") {
    const btn = document.querySelector(`.xv1-tab[data-type="${pType === "visi" ? "" : pType}"]`);
    if (btn) btn.click();
  }
  const pTopic = params.get("tema");
  if (pTopic) setTopic(decodeURIComponent(pTopic));

  booting = false;
  apply();

  // Personu meklēšanu nolaižamajā sarakstā veic assets/ms-a11y.js deleģētais
  // 'input' klausītājs (ar garumzīmju locīšanu); agrākā xv1FilterOptions bija
  // inline oninput atlikums bez izsaucēja.
})();
