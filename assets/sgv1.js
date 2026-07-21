// Meklēšanas ieteikumi (typeahead) — hero search (sākumlapa) + nav meklētājs.
// Attaches to EVERY form[data-sg-index] on the page (hero on the homepage, the
// compact nav form everywhere else). Each form binds independently and fetches
// its own suggestion index lazily from data/sg-index.json on first focus/input.
// Progressive enhancement: any failure leaves the plain GET form
// (pozicijas.html?q=) fully working.
//
// Link prefix: suggestion hrefs (politiki/…, pretrunas/…, assets/photos/…) are
// SITE-ROOT-relative, but the nav form lives on subdir pages (politiki/x.html →
// needs ../). The prefix is derived from the form's data-sg-index value
// (…/data/sg-index.json), which is already emitted with {{ assets_prefix }}.
//
// Tuple shapes MUST match src/render/search_index.py (schema v3):
//   p: [name, slug, partyShort, partyColor, hasPhoto, claims, contras, cat]
//      cat: 0=politiķis, 1=komentētājs, 2=iestāde/medijs
//   t: [topic, color, claims]
//   g: [name, short, color, claims]
//   c: [label, id, politicianName, severity, topic]   (pretrunas, v3)
(function () {
  "use strict";

  const P_NAME = 0, P_SLUG = 1, P_PARTY_SHORT = 2, P_COLOR = 3,
        P_PHOTO = 4, P_CLAIMS = 5, P_CONTRAS = 6, P_CAT = 7;
  const T_NAME = 0, T_COLOR = 1, T_COUNT = 2;
  const G_NAME = 0, G_SHORT = 1, G_COLOR = 2, G_COUNT = 3;
  const C_LABEL = 0, C_ID = 1, C_POL = 2, C_SEV = 3, C_TOPIC = 4;
  const MAX_P = 5, MAX_C = 3, MAX_I = 3, MAX_T = 4, MAX_G = 3, MAX_PR = 3,
        DEBOUNCE_MS = 120, MIN_CHARS = 2;
  const CAT_KICKERS = ["Politiķi", "Komentētāji", "Iestādes un mediji"];
  const CAT_CAPS = [MAX_P, MAX_C, MAX_I];
  const SEV_GLYPH = { direct_contradiction: "⇄", reversal: "↺", minor_shift: "≈" };

  function esc(s) {
    if (s == null) return "";
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // "jāņ" un "jan" abi atrod "Jānis" — visi LV diakritiku burti ir
  // combining-mark dekompozīcijas, tāpēc NFD + marku noņemšana pietiek.
  function sgFold(s) {
    return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }

  function initialsOf(name) {
    return name.split(/\s+/).filter(Boolean).slice(0, 2)
               .map(w => w[0].toUpperCase()).join("");
  }

  // --- Matching ---
  // Word-start prefix beats plain substring; within a band sort by count desc.
  function rank(rows, folded, q, countIdx, cap) {
    const pref = [], sub = [];
    for (let i = 0; i < rows.length; i++) {
      const hay = folded[i];
      const at = hay.indexOf(q);
      if (at < 0) continue;
      const wordStart = at === 0 || hay[at - 1] === " ";
      (wordStart ? pref : sub).push(rows[i]);
    }
    const byCount = (a, b) => (b[countIdx] || 0) - (a[countIdx] || 0);
    pref.sort(byCount); sub.sort(byCount);
    return pref.concat(sub).slice(0, cap);
  }

  // Bind one form (hero or nav). Everything below is per-form state.
  function bindForm(formEl) {
    const inputEl = formEl.querySelector("input[name=q]");
    if (!inputEl) return;

    // Prefix for site-root-relative suggestion hrefs, derived from the already
    // prefixed data-sg-index (…/data/sg-index.json → "" | "../" | "../../").
    const prefix = (formEl.dataset.sgIndex || "").replace(/data\/sg-index\.json.*$/, "");

    let index = null;        // {p, t, g, c} + precomputed folded haystacks
    let indexPromise = null;
    let failed = false;

    function loadIndex() {
      if (indexPromise) return indexPromise;
      indexPromise = fetch(formEl.dataset.sgIndex, { cache: "default" })
        .then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
        .then(d => {
          const c = d.c || [];
          index = {
            p: d.p, t: d.t, g: d.g, c: c,
            pf: d.p.map(row => sgFold(row[P_NAME])),
            tf: d.t.map(row => sgFold(row[T_NAME])),
            gf: d.g.map(row => sgFold(row[G_NAME] + " " + row[G_SHORT])),
            cf: c.map(row => sgFold(row[C_LABEL] + " " + row[C_POL] + " " + row[C_TOPIC])),
          };
          update();
        })
        .catch(e => {
          failed = true;
          console.error("sgv1: index fetch failed —", e);
        });
      return indexPromise;
    }

    // --- Dropdown ---
    const dropEl = document.createElement("div");
    dropEl.className = "sgv1-drop";
    const listId = "sgv1-listbox-" + Math.random().toString(36).slice(2, 8);
    dropEl.id = listId;
    dropEl.setAttribute("role", "listbox");
    dropEl.hidden = true;
    formEl.appendChild(dropEl);

    inputEl.setAttribute("role", "combobox");
    inputEl.setAttribute("aria-expanded", "false");
    inputEl.setAttribute("aria-controls", listId);
    inputEl.setAttribute("aria-autocomplete", "list");

    let activeIdx = -1;
    let optionEls = [];

    function close() {
      dropEl.hidden = true;
      inputEl.setAttribute("aria-expanded", "false");
      inputEl.removeAttribute("aria-activedescendant");
      activeIdx = -1;
      optionEls = [];
    }

    function setActive(n) {
      if (activeIdx >= 0 && optionEls[activeIdx]) optionEls[activeIdx].classList.remove("is-active");
      activeIdx = n;
      if (n >= 0 && optionEls[n]) {
        optionEls[n].classList.add("is-active");
        inputEl.setAttribute("aria-activedescendant", optionEls[n].id);
        optionEls[n].scrollIntoView({ block: "nearest" });
      } else {
        inputEl.removeAttribute("aria-activedescendant");
      }
    }

    function kicker(label) {
      return '<div class="sgv1-kicker">' + label + "</div>";
    }

    function personRow(row) {
      const avatar = row[P_PHOTO]
        ? '<img class="sgv1-avatar" src="' + prefix + 'assets/photos/' + esc(row[P_SLUG]) + '.jpg" alt="" width="28" height="28" loading="lazy" style="--pc: ' + esc(row[P_COLOR]) + '">'
        : '<span class="sgv1-avatar sgv1-avatar-initials" style="--pc: ' + esc(row[P_COLOR]) + '">' + esc(initialsOf(row[P_NAME])) + "</span>";
      const counts = row[P_CLAIMS] + " poz." + (row[P_CONTRAS] ? " · " + row[P_CONTRAS] + " pretr." : "");
      return '<a class="sgv1-opt" role="option" href="' + prefix + 'politiki/' + esc(row[P_SLUG]) + '.html">'
        + avatar
        + '<span class="sgv1-opt-name">' + esc(row[P_NAME]) + "</span>"
        + '<span class="sgv1-opt-sub"><span class="sgv1-dot" style="background:' + esc(row[P_COLOR]) + '"></span>' + esc(row[P_PARTY_SHORT]) + "</span>"
        + '<span class="sgv1-counts">' + counts + "</span></a>";
    }

    function contraRow(row) {
      const glyph = SEV_GLYPH[row[C_SEV]] || "·";
      const sub = esc(row[C_POL]) + (row[C_TOPIC] ? " · " + esc(row[C_TOPIC]) : "");
      return '<a class="sgv1-opt" role="option" href="' + prefix + 'pretrunas/' + esc(String(row[C_ID])) + '.html">'
        + '<span class="sgv1-contra-glyph" aria-hidden="true">' + glyph + "</span>"
        + '<span class="sgv1-opt-name">' + esc(row[C_LABEL]) + "</span>"
        + '<span class="sgv1-opt-sub">' + sub + "</span></a>";
    }

    function topicRow(row) {
      return '<a class="sgv1-opt" role="option" href="' + prefix + 'pozicijas.html?tema=' + encodeURIComponent(row[T_NAME]) + '">'
        + '<span class="sgv1-dot sgv1-dot-lg" style="background:' + esc(row[T_COLOR]) + '"></span>'
        + '<span class="sgv1-opt-name">' + esc(row[T_NAME]) + "</span>"
        + '<span class="sgv1-counts">' + row[T_COUNT] + " poz.</span></a>";
    }

    function partyRow(row) {
      return '<a class="sgv1-opt" role="option" href="' + prefix + 'partijas/' + esc(String(row[G_SHORT]).toLowerCase()) + '.html">'
        + '<span class="sgv1-dot sgv1-dot-lg" style="background:' + esc(row[G_COLOR]) + '"></span>'
        + '<span class="sgv1-opt-name">' + esc(row[G_NAME]) + "</span>"
        + '<span class="sgv1-opt-sub">' + esc(row[G_SHORT]) + "</span>"
        + '<span class="sgv1-counts">' + row[G_COUNT] + " poz.</span></a>";
    }

    function update() {
      if (failed) return;
      const raw = inputEl.value.trim();
      if (!raw) { close(); return; }
      if (!index) { loadIndex(); return; }

      const q = sgFold(raw);
      let html = "";
      if (q.length >= MIN_CHARS) {
        // Plats kandidātu logs, tad sadale pa cat sekcijām ar savu cap katrai.
        const pols = rank(index.p, index.pf, q, P_CLAIMS, MAX_P + MAX_C + MAX_I + 6);
        for (let cat = 0; cat < CAT_KICKERS.length; cat++) {
          const rows = pols.filter(r => (r[P_CAT] === undefined ? 0 : r[P_CAT]) === cat)
                           .slice(0, CAT_CAPS[cat]);
          if (rows.length) html += kicker(CAT_KICKERS[cat]) + rows.map(personRow).join("");
        }
        const contras = rank(index.c, index.cf, q, C_ID, MAX_PR);
        if (contras.length) html += kicker("Pretrunas") + contras.map(contraRow).join("");
        const tops = rank(index.t, index.tf, q, T_COUNT, MAX_T);
        const parts = rank(index.g, index.gf, q, G_COUNT, MAX_G);
        if (tops.length) html += kicker("Tēmas") + tops.map(topicRow).join("");
        if (parts.length) html += kicker("Partijas") + parts.map(partyRow).join("");
      }
      html += '<a class="sgv1-opt sgv1-submit-row" role="option" href="' + prefix + 'pozicijas.html?q=' + encodeURIComponent(raw) + '">'
        + 'Meklēt "' + esc(raw) + '" pozīcijās →</a>';

      dropEl.innerHTML = html;
      optionEls = Array.prototype.slice.call(dropEl.querySelectorAll(".sgv1-opt"));
      optionEls.forEach((el, n) => { el.id = listId + "-opt-" + n; });
      activeIdx = -1;
      dropEl.hidden = false;
      inputEl.setAttribute("aria-expanded", "true");
    }

    // --- Events ---
    let debounceTimer = null;
    let composing = false;

    inputEl.addEventListener("compositionstart", () => { composing = true; });
    inputEl.addEventListener("compositionend", () => { composing = false; update(); });

    inputEl.addEventListener("input", () => {
      if (composing) return;
      loadIndex();
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(update, DEBOUNCE_MS);
    });

    inputEl.addEventListener("focus", () => {
      loadIndex();
      if (inputEl.value.trim()) update();
    });

    inputEl.addEventListener("keydown", (e) => {
      if (dropEl.hidden || !optionEls.length) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActive((activeIdx + 1) % optionEls.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive((activeIdx - 1 + optionEls.length) % optionEls.length);
      } else if (e.key === "Enter") {
        if (activeIdx >= 0 && optionEls[activeIdx]) {
          e.preventDefault();
          window.location.href = optionEls[activeIdx].href;
        }
        // bez aktīvas opcijas — dabiskais form submit uz pozicijas.html?q=
      } else if (e.key === "Escape") {
        close();
      }
    });

    // Klikšķis dropdownā notiek pirms input blur — mousedown preventDefault
    // notur fokusu, lai navigācija nostrādā.
    dropEl.addEventListener("mousedown", (e) => { e.preventDefault(); });

    document.addEventListener("pointerdown", (e) => {
      if (!formEl.contains(e.target)) close();
    });
  }

  const forms = document.querySelectorAll("form[data-sg-index]");
  for (let i = 0; i < forms.length; i++) bindForm(forms[i]);
})();
