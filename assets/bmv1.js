/*
 * Balsojumu matricas renderer (Step 2 of virtualization plan).
 * Source: assets/bmv1.js → copied to output/atmina/assets/bmv1.js.
 *
 * Fetches /data/balsojumi-matrica.json (compact format from
 * src/render/votes.py::_emit_matrix_json) and renders the deputy×vote
 * matrix client-side. Lazy: first activates only when user opens the
 * "Matrica" tab, so most visitors never download the JSON.
 *
 * Smart default: shows the last 60 days of votes (~50 columns × ~135
 * deputies = 6,750 cells). "Visa vēsture" expands to all 5,703+ votes
 * behind a confirm dialog (770k cells take 2-5s to render). Filters
 * (faction, single-session, "tikai strīdīgie", vote-type highlight)
 * operate on the JSON state; the table re-renders in one innerHTML
 * write so DOM updates stay fast.
 *
 * Vote-string encoding (matches meta.encoding field):
 *   P = Par, N = Pret, A = Atturas, X = Nebalsoja, '.' = absent.
 *
 * Plan: docs/superpowers/plans/archive/2026-05-28-balsojumi-virtualization.md
 */
(function () {
  "use strict";

  var ROOT = null;
  var DATA = null; // parsed JSON (recent shard by default; full archive once loaded)
  var RECENT_SRC = null; // recent-shard URL (default matrix payload)
  var FULL_SRC = null; // full-archive URL, fetched lazily on "Visa vēsture"/deep-link
  var fullLoaded = false;
  var STATE = {
    range: 60, // 'session' | 7 | 30 | 60 | 365 | 'all'
    confirmedAll: false,
    hiddenFactions: new Set(),
    sessionDate: "",
    stridgieOnly: false,
    showProcedural: false, // default hide attendance/breaks/referrals
    voteHighlight: null, // {voteIdx, voteChar}
    activePid: null,
    activeVoteIdx: null,
  };

  var VOTE_LABEL = { P: "Par", N: "Pret", A: "Atturas", X: "Nebalsoja", ".": "Nepiedalījās" };
  var VOTE_CLASS = { P: "vote-par", N: "vote-pret", A: "vote-atturas", X: "vote-nebalso", ".": "vote-absent" };
  var VOTE_GLYPH = { P: "&#10003;", N: "&#10007;", A: "&#9675;", X: "NB", ".": "" };
  var VOTE_TITLE = {
    P: "Par",
    N: "Pret",
    A: "Atturas",
    X: "Nebalsoja (re&#291;istr&#275;ts, bet nebalsoja)",
    ".": "Nepiedalījās",
  };

  var initOnce = false;

  // ── Public entry point ───────────────────────────────────────────
  // recentSrc = small ~1-year shard loaded by default; fullSrc = ever-growing
  // archive fetched lazily only when the user opens "Visa vēsture" or deep-links
  // to a vote older than the recent window. fullSrc is optional (falls back to
  // recentSrc) so the renderer still works if only one source is wired.
  window.initBalsojumiMatrica = function (root, recentSrc, fullSrc) {
    if (initOnce) return;
    initOnce = true;
    ROOT = root;
    RECENT_SRC = RECENT_SRC || recentSrc;
    FULL_SRC = FULL_SRC || fullSrc || recentSrc;
    renderSkeleton();
    // If TAB-1 archive mode already fetched data into DATA, reuse it (full is a
    // superset; the matrix range-filters for display anyway) — no refetch.
    ensureData(
      false,
      function () {
        renderShell();
        applyHashScroll();
      },
      function (msg) {
        renderError(msg);
      },
    );
  };

  // ── Shared data loader ───────────────────────────────────────────
  // Fetch+parse a JSON shard into DATA. markFull flags the full archive so
  // ensureData() knows the superset is present. cb(DATA) on success; errcb(msg)
  // on failure (callers decide how to surface it — matrix vs archive differ).
  function loadInto(src, markFull, cb, errcb) {
    fetch(src, { credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (json) {
        if (!json || !json.votes || !json.politicians) {
          throw new Error("JSON struktūra nederīga");
        }
        DATA = json;
        if (markFull) fullLoaded = true;
        cb(DATA);
      })
      .catch(function (err) {
        (errcb || function () {})(
          err && err.message ? err.message : "nezināma kļūda",
        );
      });
  }

  // Unified data ensure shared by the matrix and TAB-1 archive mode.
  //   wantFull=false → recent shard is enough (matrix default view).
  //   wantFull=true  → must have the full archive ("Visa vēsture", deep-link,
  //                    or any TAB-1 filter that spans all history).
  // Idempotent: returns the already-loaded DATA when it satisfies the request.
  function ensureData(wantFull, cb, errcb) {
    if (DATA && (!wantFull || fullLoaded)) {
      cb(DATA);
      return;
    }
    var src = wantFull ? FULL_SRC || RECENT_SRC : RECENT_SRC || FULL_SRC;
    loadInto(src, !!wantFull, cb, errcb);
  }

  // Fetch the full archive once, swap it into DATA, then run cb(). Used when the
  // user opens "Visa vēsture" or deep-links to a vote outside the recent shard.
  function ensureFullData(cb) {
    if (fullLoaded || !FULL_SRC) {
      cb();
      return;
    }
    var info = document.getElementById("matrix-range-info");
    if (info) info.textContent = "Ielādē visu vēsturi…";
    ensureData(true, cb, function (msg) {
      renderError(msg);
    });
  }

  // ── Initial states ───────────────────────────────────────────────
  function renderSkeleton() {
    ROOT.innerHTML =
      '<div class="matrix-loading" style="padding:2rem; text-align:center; color:var(--text-muted);">' +
      "Ielādē balsojumu matricu…" +
      "</div>";
  }

  function renderError(msg) {
    ROOT.innerHTML =
      '<div class="matrix-error" style="padding:2rem; text-align:center;">' +
      '<p style="color:var(--text-muted);">Matricu neizdevās ielādēt: ' +
      escHtml(msg) +
      "</p>" +
      '<p style="font-size:0.9rem;"><a href="personas.html">Apskati deputātus profilos →</a></p>' +
      "</div>";
  }

  // ── Shell layout ─────────────────────────────────────────────────
  function renderShell() {
    var rangeButtons = [
      { key: "session", label: "Šī sēde" },
      { key: 7, label: "7 d" },
      { key: 30, label: "30 d" },
      { key: 60, label: "60 d" },
      { key: 365, label: "1 gads" },
      { key: "all", label: "Visa vēsture" },
    ];
    var rangeHtml = rangeButtons
      .map(function (b) {
        var active = String(b.key) === String(STATE.range) ? " active" : "";
        return (
          '<button class="matrix-range-btn' +
          active +
          '" data-range="' +
          b.key +
          '">' +
          escHtml(b.label) +
          "</button>"
        );
      })
      .join("");

    var factionHtml = DATA.factions
      .map(function (f) {
        return (
          '<button class="link-filter-btn active matrix-faction-filter" ' +
          'data-faction="' +
          escAttr(f.f) +
          '" style="--filter-color: ' +
          escAttr(f.c) +
          ';">' +
          '<span class="filter-dot" style="background:' +
          escAttr(f.c) +
          ';"></span>' +
          escHtml(f.f) +
          ' <span class="filter-count">' +
          f.m.length +
          "</span></button>"
        );
      })
      .join("");

    // Session select lists EVERY session (meta.all_dates) even when only the
    // recent shard is loaded — picking one outside the shard triggers a lazy
    // full-archive fetch (see selectSession). Fall back to the loaded shard's
    // own dates if meta.all_dates is absent (older JSON / standalone use).
    var sortedDates =
      DATA.meta && DATA.meta.all_dates && DATA.meta.all_dates.length
        ? DATA.meta.all_dates.slice()
        : (function () {
            var dd = {};
            DATA.votes.forEach(function (v) {
              dd[v.d] = true;
            });
            return Object.keys(dd).sort().reverse();
          })();
    var sessionOptions =
      '<option value="">Visas sēdes</option>' +
      sortedDates
        .map(function (d) {
          return '<option value="' + escAttr(d) + '">' + lvDate(d) + "</option>";
        })
        .join("");

    ROOT.innerHTML =
      '<div class="matrix-range-bar" style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-bottom:0.75rem; align-items:center;">' +
      '<span style="color:var(--text-muted); font-size:0.85rem;">Rāda:</span>' +
      rangeHtml +
      '<span id="matrix-range-info" style="color:var(--text-muted); font-size:0.8rem; margin-left:0.5rem;"></span>' +
      "</div>" +
      '<div class="matrix-filter-bar">' +
      factionHtml +
      '<span style="border-left:1px solid var(--border);height:1.5rem;margin:0 0.25rem;"></span>' +
      '<select id="matrix-session-select" class="matrix-select"><option value="">Visas sēdes</option></select>' +
      // "Tikai strīdīgie" nepateica, pēc kā tiek šķirots. `uni` karogs atzīmē
      // vienbalsīgos, tāpēc filtrs burtiski atmet tos — tā to arī sauc.
      '<button class="matrix-toggle" id="matrix-stridgie-toggle" aria-pressed="false" ' +
      'title="Rāda tikai balsojumus, kuros deputāti nebija vienoti — vienbalsīgie tiek izlaisti.">Tikai nevienbalsīgie</button>' +
      // Iepriekšējais "Procedurālie" neatklāja, vai poga tos rāda vai slēpj.
      // Etiķete tagad nosauc STĀVOKLI un mainās līdz ar to (sk. bindShellEvents).
      '<button class="matrix-toggle" id="matrix-procedural-toggle" aria-pressed="false" ' +
      'title="Procedurālie = klātbūtnes reģistrācija, sēžu pārtraukumi, darba kārtība, nodošana komisijām, mandāta jautājumi.">' +
      proceduralLabel() +
      "</button>" +
      "</div>" +
      // Simbolu leģenda. Bez tās starpība starp "NB" (reģistrējies, bet balsi
      // nenodeva) un tukšu šūnu (sēdē nepiedalījās) nav uzminama.
      '<div class="matrix-legend" aria-label="Simbolu apzīmējumi">' +
      '<span class="matrix-legend-item"><span class="matrix-legend-glyph vote-par">' + VOTE_GLYPH.P + "</span> Par</span>" +
      '<span class="matrix-legend-item"><span class="matrix-legend-glyph vote-pret">' + VOTE_GLYPH.N + "</span> Pret</span>" +
      '<span class="matrix-legend-item"><span class="matrix-legend-glyph vote-atturas">' + VOTE_GLYPH.A + "</span> Atturas — skaitās klātbūtnē, tāpēc gāž priekšlikumu tāpat kā „pret&#8221;</span>" +
      '<span class="matrix-legend-item"><span class="matrix-legend-glyph vote-nebalso">NB</span> reģistrējies, bet balsi nenodeva</span>' +
      '<span class="matrix-legend-item"><span class="matrix-legend-glyph vote-absent">&#183;</span> sēdē nepiedalījās</span>' +
      "</div>" +
      '<div class="matrix-split">' +
      '<div class="matrix-pane" id="matrix-scroll">' +
      '<div id="matrix-table-wrap"></div>' +
      "</div>" +
      '<div class="matrix-detail-pane" id="matrix-detail-pane">' +
      '<div class="detail-pane-empty" id="matrix-detail-empty">' +
      '<span class="hint-icon">&#9638;</span>' +
      "<p>Uzklikšķini uz <strong>balsojuma</strong> vai <strong>deputāta</strong></p>" +
      "</div>" +
      '<div id="matrix-detail-content" style="display: none;"></div>' +
      "</div>" +
      "</div>";

    // Populate session select. We do it post-innerHTML because building
    // sortedDates per-render is fine but mounting a huge <select> via
    // string concat into the shell template is noisier.
    var sel = document.getElementById("matrix-session-select");
    sel.innerHTML = sessionOptions;
    // Restore the active session across renderShell rebuilds (e.g. after the
    // full archive loads for an out-of-shard session pick).
    sel.value = STATE.sessionDate || "";

    bindShellEvents();
    render();
    renderDefaultDetail();
  }

  // Tukšais "Uzklikšķini uz balsojuma vai deputāta" aizņēma trešdaļu ekrāna un
  // neko nepateica. Vietā — pēdējās sēdes kopsavilkums no jau ielādētajiem
  // datiem. Rādās TIKAI tad, kad lietotājs vēl neko nav izvēlējies; jebkura
  // izvēle to aizstāj un vairs neatgriež.
  function renderDefaultDetail() {
    if (STATE.activePid !== null || STATE.activeVoteIdx !== null) return;
    var empty = document.getElementById("matrix-detail-empty");
    if (!empty) return;
    var votes = DATA.votes || [];
    if (!votes.length) return;
    var lastDate = votes[votes.length - 1].d;
    var dayIdx = [];
    for (var i = votes.length - 1; i >= 0 && votes[i].d === lastDate; i--) dayIdx.push(i);
    var total = dayIdx.length;
    var splitN = 0;
    var procN = 0;
    for (var k = 0; k < dayIdx.length; k++) {
      var v = votes[dayIdx[k]];
      if (voteIsSplit(v)) splitN++;
      if (v.proc) procN++;
    }
    var html =
      '<div class="detail-default">' +
      '<div class="detail-section-title">Pēdējā sēde</div>' +
      "<h3>" + escHtml(lvDate(lastDate)) + "</h3>" +
      '<ul class="detail-default-list">' +
      "<li><strong>" + total + "</strong> " + lvPlural(total, "balsojums", "balsojumi") + "</li>" +
      "<li><strong>" + splitN + "</strong> ar dalītu frakciju</li>" +
      "<li><strong>" + procN + "</strong> " + lvPlural(procN, "procedurāls", "procedurāli") + "</li>" +
      "</ul>" +
      '<p><a href="#" class="matrix-goto-list" data-date="' + escAttr(lastDate) +
      '">Skatīt šīs sēdes balsojumus sarakstā &#8594;</a></p>' +
      '<p class="detail-hint">Uzklikšķini uz kolonnas galvenes vai deputāta vārda, lai redzētu detaļas.</p>' +
      "</div>";
    empty.innerHTML = html;
    empty.classList.add("has-default");
    var link = empty.querySelector(".matrix-goto-list");
    if (link) {
      link.addEventListener("click", function (e) {
        e.preventDefault();
        // blv1.js reģistrē šo āķi; ja tā nav (atsevišķa lapa/tests), saite
        // vienkārši neko nedara, nevis met kļūdu.
        if (typeof window.balsojumiSelectSession === "function") {
          window.balsojumiSelectSession(link.dataset.date);
        }
      });
    }
  }

  function bindShellEvents() {
    ROOT.querySelectorAll(".matrix-range-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var k = btn.dataset.range;
        var range = k === "all" ? "all" : k === "session" ? "session" : parseInt(k, 10);
        setRange(range);
      });
    });
    ROOT.querySelectorAll(".matrix-faction-filter").forEach(function (btn) {
      btn.addEventListener("click", function () {
        toggleFaction(btn);
      });
    });
    document.getElementById("matrix-session-select").addEventListener("change", function (e) {
      selectSession(e.target.value);
    });
    document.getElementById("matrix-stridgie-toggle").addEventListener("click", function (e) {
      STATE.stridgieOnly = !STATE.stridgieOnly;
      e.currentTarget.classList.toggle("active", STATE.stridgieOnly);
      e.currentTarget.setAttribute("aria-pressed", STATE.stridgieOnly ? "true" : "false");
      render();
    });
    document.getElementById("matrix-procedural-toggle").addEventListener("click", function (e) {
      STATE.showProcedural = !STATE.showProcedural;
      e.currentTarget.classList.toggle("active", STATE.showProcedural);
      e.currentTarget.setAttribute("aria-pressed", STATE.showProcedural ? "true" : "false");
      e.currentTarget.textContent = proceduralLabel();
      render();
    });
  }

  // Pogas etiķete nosauc pašreizējo stāvokli, nevis darbību — "Procedurālie"
  // vien neatklāja, vai tie tobrīd ir redzami vai slēpti.
  function proceduralLabel() {
    return STATE.showProcedural ? "Procedurālie: redzami" : "Procedurālie: slēpti";
  }

  // ── Filter manipulators ──────────────────────────────────────────
  // Selecting a session overrides the date-range filter and pulls the full
  // archive when the chosen date is outside the loaded (recent) shard — so any
  // session in the dropdown "just works" without the user knowing shards exist.
  function selectSession(dateStr) {
    STATE.sessionDate = dateStr;
    var inShard =
      !dateStr ||
      DATA.votes.some(function (v) {
        return v.d === dateStr;
      });
    if (inShard) {
      render();
    } else {
      ensureFullData(function () {
        // Full data now present — rebuild the shell (repopulates the dropdown,
        // restores the selection via sel.value) and re-render to the session.
        renderShell();
      });
    }
  }

  // "Visa vēsture" needs the full archive — fetch it first, then apply the range.
  function setRange(range) {
    if (range === "all") {
      ensureFullData(function () {
        applyRange(range);
      });
      return;
    }
    applyRange(range);
  }
  function applyRange(range) {
    STATE.range = range;
    STATE.confirmedAll = false;
    ROOT.querySelectorAll(".matrix-range-btn").forEach(function (b) {
      b.classList.toggle("active", String(b.dataset.range) === String(range));
    });
    render();
  }

  function toggleFaction(btn) {
    var faction = btn.dataset.faction;
    btn.classList.toggle("active");
    if (STATE.hiddenFactions.has(faction)) STATE.hiddenFactions.delete(faction);
    else STATE.hiddenFactions.add(faction);
    render();
  }

  // ── Compute visible indices ──────────────────────────────────────
  function computeVisibleVoteIndices() {
    var votes = DATA.votes;
    var n = votes.length;
    var startIdx = 0;

    // Range filter (date-based, defaults to last 60 days). A specific session
    // pick overrides the range entirely — scan all loaded votes so the chosen
    // date is always found (the date filter below narrows to it).
    if (STATE.sessionDate) {
      startIdx = 0;
    } else if (STATE.range === "all") {
      startIdx = 0;
    } else if (STATE.range === "session") {
      // Latest sēde date — find rightmost date and include all matching votes.
      var latestDate = votes.length ? votes[n - 1].d : "";
      startIdx = n;
      for (var i = 0; i < n; i++) {
        if (votes[i].d === latestDate) {
          startIdx = i;
          break;
        }
      }
    } else {
      var days = STATE.range;
      var latest = votes.length ? votes[n - 1].d : "";
      var cutoff = subtractDays(latest, days);
      startIdx = n;
      for (var j = 0; j < n; j++) {
        if (votes[j].d >= cutoff) {
          startIdx = j;
          break;
        }
      }
    }

    var indices = [];
    for (var k = startIdx; k < n; k++) {
      var v = votes[k];
      if (!STATE.showProcedural && v.proc) continue;
      if (STATE.sessionDate && v.d !== STATE.sessionDate) continue;
      if (STATE.stridgieOnly && v.uni) continue;
      indices.push(k);
    }
    return indices;
  }

  function computeVisibleFactions() {
    return DATA.factions.filter(function (f) {
      return !STATE.hiddenFactions.has(f.f);
    });
  }

  // ── Main render ──────────────────────────────────────────────────
  function render() {
    var visIdx = computeVisibleVoteIndices();
    var visFactions = computeVisibleFactions();

    // Confirm gate for very large renders (full history mode).
    if (visIdx.length > 2000 && !STATE.confirmedAll) {
      renderConfirmGate(visIdx.length);
      return;
    }

    var totalDeputies = visFactions.reduce(function (n, f) {
      return n + f.m.length;
    }, 0);

    var info = document.getElementById("matrix-range-info");
    if (info) {
      var procHidden = 0;
      if (!STATE.showProcedural) {
        for (var pi = 0; pi < DATA.votes.length; pi++) {
          if (DATA.votes[pi].proc) procHidden++;
        }
      }
      info.textContent =
        visIdx.length +
        " / " +
        DATA.meta.votes_total +
        " balsojumi · " +
        totalDeputies +
        " deputāti" +
        (procHidden ? " · " + procHidden + " procedurālie slēpti" : "");
    }

    var wrap = document.getElementById("matrix-table-wrap");
    if (visIdx.length === 0) {
      wrap.innerHTML =
        '<div class="matrix-empty" style="padding:2rem; text-align:center; color:var(--text-muted);">' +
        "Nav balsojumu, kas atbilst izvēlētajiem filtriem." +
        "</div>";
      return;
    }

    wrap.innerHTML = renderMatrixHtml(visIdx, visFactions);
    bindMatrixEvents();
    if (STATE.voteHighlight !== null) reapplyHighlight();
  }

  function renderConfirmGate(n) {
    var wrap = document.getElementById("matrix-table-wrap");
    wrap.innerHTML =
      '<div class="matrix-confirm" style="padding:2rem; text-align:center; max-width:520px; margin:0 auto;">' +
      '<h3 style="margin-bottom:0.5rem;">Rādīt visu vēsturi?</h3>' +
      '<p style="color:var(--text-muted); margin-bottom:1rem;">' +
      "Tiks renderēti <strong>" +
      n +
      "</strong> balsojumi × " +
      "<strong>" +
      Object.keys(DATA.politicians).length +
      "</strong> deputāti. " +
      "Atkarībā no ierīces, tas var prasīt 2–5 sekundes." +
      "</p>" +
      '<button id="matrix-confirm-yes" class="matrix-toggle active" style="margin-right:0.5rem;">Rādīt visu</button>' +
      '<button id="matrix-confirm-no" class="matrix-toggle">Atcelt</button>' +
      "</div>";
    document.getElementById("matrix-confirm-yes").addEventListener("click", function () {
      STATE.confirmedAll = true;
      render();
    });
    document.getElementById("matrix-confirm-no").addEventListener("click", function () {
      setRange(60);
    });
  }

  function renderMatrixHtml(visIdx, visFactions) {
    var v = DATA.votes;
    var hdr = ['<table class="matrix-table" id="matrix-table"><thead><tr>'];
    hdr.push('<th class="matrix-corner matrix-col-name">Deputāts</th>');
    hdr.push('<th class="matrix-corner-faction matrix-col-faction">Frakcija</th>');
    // Kolonnas galvene: motīvs (nocirsts) + datums + iznākuma punkts. Datums
    // bija galvenes lielākais robs — 40 zīmju nocirpums bez datuma nepateica,
    // par kuru sēdi kolonna runā. Pilnais motīvs paliek `title` un detaļu panelī.
    var curYear = String(new Date().getFullYear());
    for (var i = 0; i < visIdx.length; i++) {
      var vi = visIdx[i];
      var vc = v[vi];
      var full = vc.m || "";
      var short = full.substring(0, 40);
      var dLabel = shortDate(vc.d, curYear);
      var dotTitle = vc.r ? String(vc.r) : "Iznākums nav norādīts";
      hdr.push(
        '<th class="matrix-vote-header" data-vote-idx="' +
          vi +
          '"><span class="matrix-vote-head">' +
          '<span class="matrix-vote-label" title="' +
          escAttr(full + " · " + lvDate(vc.d) + (vc.r ? " · " + vc.r : "")) +
          '">' +
          escHtml(short) +
          (full.length > 40 ? "…" : "") +
          "</span>" +
          '<span class="matrix-vote-date">' +
          escHtml(dLabel) +
          "</span>" +
          '<span class="matrix-vote-dot ' +
          resultDotClass(vc.r) +
          '" title="' +
          escAttr(dotTitle) +
          '"></span>' +
          "</span></th>",
      );
    }
    hdr.push("</tr></thead><tbody>");

    var body = [];
    for (var fi = 0; fi < visFactions.length; fi++) {
      var f = visFactions[fi];
      body.push(
        '<tr class="matrix-faction-row" data-faction="' +
          escAttr(f.f) +
          '" style="--faction-color: ' +
          escAttr(f.c) +
          ';"><td colspan="' +
          (visIdx.length + 2) +
          '">' +
          escHtml(f.f) +
          "</td></tr>",
      );
      for (var mi = 0; mi < f.m.length; mi++) {
        var pid = f.m[mi];
        var pol = DATA.politicians[String(pid)];
        if (!pol) continue;
        body.push(
          '<tr data-faction="' +
            escAttr(f.f) +
            '" data-pid="' +
            pid +
            '">' +
            '<td class="matrix-col-name" data-pid="' +
            pid +
            '">' +
            escHtml(pol.n) +
            "</td>" +
            '<td class="matrix-col-faction">' +
            escHtml(f.f) +
            "</td>",
        );
        for (var k = 0; k < visIdx.length; k++) {
          var idx = visIdx[k];
          var ch = pol.v.charAt(idx) || ".";
          body.push(
            '<td class="matrix-cell ' +
              VOTE_CLASS[ch] +
              '" data-vote-idx="' +
              idx +
              '" title="' +
              VOTE_TITLE[ch] +
              '">' +
              VOTE_GLYPH[ch] +
              "</td>",
          );
        }
        body.push("</tr>");
      }
    }
    body.push("</tbody></table>");
    return hdr.join("") + body.join("");
  }

  function bindMatrixEvents() {
    var table = document.getElementById("matrix-table");
    if (!table) return;
    table.addEventListener("click", function (e) {
      var nameCell = e.target.closest(".matrix-col-name[data-pid]");
      if (nameCell) {
        showPoliticianDetail(parseInt(nameCell.dataset.pid, 10));
        return;
      }
      var hdr = e.target.closest(".matrix-vote-header[data-vote-idx]");
      if (hdr) {
        showVoteDetail(parseInt(hdr.dataset.voteIdx, 10));
        return;
      }
      var cell = e.target.closest("td.matrix-cell[data-vote-idx]");
      if (cell) {
        showVoteDetail(parseInt(cell.dataset.voteIdx, 10));
      }
    });
  }

  // ── Vote highlight (filter by Par/Pret/Atturas on a single vote) ─
  function filterByVoteType(voteIdx, ch) {
    if (
      STATE.voteHighlight &&
      STATE.voteHighlight.voteIdx === voteIdx &&
      STATE.voteHighlight.voteChar === ch
    ) {
      STATE.voteHighlight = null;
    } else {
      STATE.voteHighlight = { voteIdx: voteIdx, voteChar: ch };
    }
    reapplyHighlight();
  }

  function reapplyHighlight() {
    var rows = document.querySelectorAll("#matrix-table tbody tr[data-pid]");
    rows.forEach(function (row) {
      row.classList.remove("matrix-row-dimmed");
      row.classList.remove("matrix-row-highlighted");
    });
    if (!STATE.voteHighlight) return;
    var idx = STATE.voteHighlight.voteIdx;
    var ch = STATE.voteHighlight.voteChar;
    rows.forEach(function (row) {
      var pid = row.dataset.pid;
      var pol = DATA.politicians[pid];
      if (!pol) return;
      var actual = pol.v.charAt(idx) || ".";
      if (actual === ch) row.classList.add("matrix-row-highlighted");
      else row.classList.add("matrix-row-dimmed");
    });
  }

  // ── Detail panels ────────────────────────────────────────────────
  function showVoteDetail(voteIdx) {
    var vote = DATA.votes[voteIdx];
    if (!vote) return;
    STATE.activeVoteIdx = voteIdx;
    document.querySelectorAll(".matrix-vote-header.active").forEach(function (el) {
      el.classList.remove("active");
    });
    document
      .querySelectorAll('.matrix-vote-header[data-vote-idx="' + voteIdx + '"]')
      .forEach(function (el) {
        el.classList.add("active");
      });
    STATE.voteHighlight = null;
    reapplyHighlight();

    var resultClass = resultBadgeClass(vote.r);
    var html = '<h3 style="font-size:1rem; margin-bottom:0.5rem;">' + escHtml(vote.m) + "</h3>";
    if (vote.s) {
      html +=
        '<p style="font-size:0.82rem; color:var(--text-muted); line-height:1.5; margin-bottom:0.75rem;">' +
        escHtml(vote.s) +
        "</p>";
    }
    html += '<div class="detail-meta">';
    html += '<span class="badge ' + resultClass + '">' + escHtml(vote.r) + "</span>";
    html +=
      '<span class="badge badge-green vote-filter-btn" data-vote-idx="' +
      voteIdx +
      '" data-vote-char="P" title="Filtrēt: rādīt tikai Par">Par: ' +
      vote.tot[0] +
      "</span>";
    html +=
      '<span class="badge badge-red vote-filter-btn" data-vote-idx="' +
      voteIdx +
      '" data-vote-char="N" title="Filtrēt: rādīt tikai Pret">Pret: ' +
      vote.tot[1] +
      "</span>";
    html +=
      '<span class="badge badge-yellow vote-filter-btn" data-vote-idx="' +
      voteIdx +
      '" data-vote-char="A" title="Filtrēt: rādīt tikai Atturas">Atturas: ' +
      vote.tot[2] +
      "</span>";
    html += "</div>";
    html +=
      '<p style="font-size:0.75rem; color:var(--text-muted); margin-bottom:0.5rem; font-style:italic;">' +
      "Uzklikšķini uz Par/Pret/Atturas lai filtrētu matricu</p>";
    html +=
      '<p style="font-size:0.8rem; color:var(--text-muted); margin-bottom:0.75rem;">' +
      escHtml(lvDate(vote.d)) +
      (vote.t ? " " + escHtml(vote.t) : "") +
      "</p>";

    if (vote.f && vote.f.length) {
      html += '<hr class="detail-divider"><div class="detail-section-title">Frakciju sadalījums</div>';
      html +=
        '<p class="detail-hint">Josla: par / pret / atturas / nebalsoja</p>';
      // Saucējs satur arī nebalsojušos (`x`), tāpēc arī tiem ir savs segments.
      // Bez tā frakcijā ar daudz NB josla vizuāli neaizpildījās līdz galam un
      // izskatījās kā trūkstoši dati.
      vote.f.forEach(function (fb) {
        var nb = fb.x || 0;
        var total = (fb.p || 0) + (fb.n || 0) + (fb.a || 0) + nb;
        if (total === 0) return;
        var pPar = (((fb.p || 0) / total) * 100).toFixed(1);
        var pPret = (((fb.n || 0) / total) * 100).toFixed(1);
        var pAtt = (((fb.a || 0) / total) * 100).toFixed(1);
        var pNb = ((nb / total) * 100).toFixed(1);
        html +=
          '<div class="faction-bar-row"' +
          (factionIsSplit(fb) ? ' title="Dalīts balsojums — frakcija nebija vienota."' : "") +
          ">" +
          '<span class="faction-bar-label">' +
          escHtml(fb.f) +
          "</span>" +
          '<div class="faction-bar-track">' +
          '<div class="faction-bar-seg bmv1-seg-par" style="width:' +
          pPar +
          '%;"></div>' +
          '<div class="faction-bar-seg bmv1-seg-pret" style="width:' +
          pPret +
          '%;"></div>' +
          '<div class="faction-bar-seg bmv1-seg-att" style="width:' +
          pAtt +
          '%;"></div>' +
          '<div class="faction-bar-seg bmv1-seg-nb" style="width:' +
          pNb +
          '%;"></div>' +
          "</div>" +
          '<span class="faction-bar-counts">' +
          fb.p +
          "/" +
          fb.n +
          "/" +
          fb.a +
          "/" +
          nb +
          "</span>" +
          "</div>";
      });
    }

    html += '<hr class="detail-divider">';
    if (vote.url) {
      html +=
        '<a href="' +
        escAttr(vote.url) +
        '" target="_blank" rel="noopener" style="font-size:0.82rem; display:block; margin-bottom:0.3rem;">Balsojuma tabula &#8599;</a>';
    }
    if (vote.doc_url) {
      html +=
        '<a href="' +
        escAttr(vote.doc_url) +
        '" target="_blank" rel="noopener" style="font-size:0.82rem; display:block;">Likumprojekts &#8599;</a>';
    }
    showDetailContent(html);

    // Bind the Par/Pret/Atturas pseudo-filter buttons inside the panel.
    document
      .querySelectorAll("#matrix-detail-content .vote-filter-btn[data-vote-char]")
      .forEach(function (btn) {
        btn.addEventListener("click", function () {
          filterByVoteType(
            parseInt(btn.dataset.voteIdx, 10),
            btn.dataset.voteChar,
          );
        });
      });
  }

  function showPoliticianDetail(pid) {
    var person = DATA.politicians[String(pid)];
    if (!person) return;
    STATE.activePid = pid;
    document.querySelectorAll(".matrix-row-active").forEach(function (el) {
      el.classList.remove("matrix-row-active");
    });
    document.querySelectorAll(".matrix-vote-header.active").forEach(function (el) {
      el.classList.remove("active");
    });
    var row = document.querySelector('tr[data-pid="' + pid + '"]');
    if (row) row.classList.add("matrix-row-active");

    var totalVotes = person.sum[0] + person.sum[1] + person.sum[2] + person.sum[3];
    var attended = person.sum[0] + person.sum[1] + person.sum[2];
    var attendPct = totalVotes > 0 ? Math.round((attended / totalVotes) * 100) : 0;

    var html = '<h3 style="font-size:1rem; margin-bottom:0.25rem;">' + escHtml(person.n) + "</h3>";
    html += '<div class="detail-subtitle">' + escHtml(person.f) + "</div>";
    if (person.s) {
      html +=
        '<a href="politiki/' +
        escAttr(person.s) +
        '.html" style="font-size:0.82rem; display:block; margin-bottom:0.75rem;">Profils &#8599;</a>';
    }
    html += '<div style="display:flex; flex-wrap:wrap; gap:0.5rem; margin-bottom:1rem;">';
    html +=
      '<span class="detail-stat"><strong class="bmv1-stat-par">' +
      person.sum[0] +
      "</strong> Par</span>";
    html +=
      '<span class="detail-stat"><strong class="bmv1-stat-pret">' +
      person.sum[1] +
      "</strong> Pret</span>";
    html +=
      '<span class="detail-stat"><strong class="bmv1-stat-att">' +
      person.sum[2] +
      "</strong> Atturas</span>";
    html += '<span class="detail-stat"><strong>' + person.sum[3] + "</strong> NB</span>";
    html += "</div>";
    html +=
      '<div style="font-size:0.8rem; color:var(--text-muted); margin-bottom:0.25rem;">Apmeklējums: ' +
      attendPct +
      "%</div>";
    html +=
      '<div class="attendance-bar"><div class="attendance-bar-fill" style="width:' +
      attendPct +
      '%;"></div></div>';
    // Tvēruma etiķete. `sum`/`att` ir aprēķināti pār VISU ielādēto shardu, ne
    // pār redzamo diapazonu — pārslēdzot 7 d → 60 d skaitļi nemainās, un bez
    // šīs rindas tie izskatījās kā skaitļi par redzamo. Skaitīšana NAV mainīta,
    // tikai nosaukts, ko tā aptver.
    html += '<p class="detail-hint">' + escHtml(loadedScopeLabel()) + "</p>";

    if (person.dis && person.dis.length) {
      html += '<hr class="detail-divider">';
      html +=
        '<div class="detail-section-title">Strīdīgie balsojumi (' +
        person.dis.length +
        ")</div>";
      person.dis.forEach(function (dv) {
        var vote = DATA.votes[dv.i];
        if (!vote) return;
        var voteLabel = VOTE_LABEL[dv.v] || dv.v;
        var voteClass =
          dv.v === "P" ? "badge-green" : dv.v === "N" ? "badge-red" : dv.v === "A" ? "badge-yellow" : "badge-muted";
        var majLabel = VOTE_LABEL[dv.fm] || dv.fm;
        html +=
          '<div class="stridgie-item">' +
          '<div class="stridgie-motif">' +
          escHtml((vote.m || "").substring(0, 80)) +
          "</div>" +
          '<div class="stridgie-meta"><span class="badge ' +
          voteClass +
          '">' +
          escHtml(voteLabel) +
          "</span> (frakcija: " +
          escHtml(majLabel) +
          ")</div>" +
          "</div>";
      });
    }
    showDetailContent(html);
  }

  // Cik plašs ir ielādētais korpuss — nosaukts, nevis noklusēts. `fullLoaded`
  // šķir pilno arhīvu no ~gada shard'a; datumus lasa no pašiem datiem, tāpēc
  // etiķete nevar novecot attiecībā pret to, kas tiešām ielādēts.
  function loadedScopeLabel() {
    var n = (DATA.votes || []).length;
    if (!n) return "Nav ielādētu balsojumu.";
    var from = lvDate(DATA.votes[0].d);
    var to = lvDate(DATA.votes[n - 1].d);
    var scope = fullLoaded ? "visu vēsturi" : "ielādēto periodu";
    return (
      "Skaitļi aptver " + scope + " (" + from + "–" + to + ", " + n + " " +
      lvPlural(n, "balsojums", "balsojumi") + "), nevis tikai redzamo izlasi."
    );
  }

  function showDetailContent(html) {
    var empty = document.getElementById("matrix-detail-empty");
    var content = document.getElementById("matrix-detail-content");
    if (empty) empty.style.display = "none";
    if (content) {
      content.innerHTML = html;
      content.style.display = "";
    }
  }

  // ── Hash navigation (#vote-N) ────────────────────────────────────
  function applyHashScroll() {
    if (!location.hash || location.hash.indexOf("#vote-") !== 0) return;
    var voteId = parseInt(location.hash.slice(6), 10);
    if (isNaN(voteId)) return;
    scrollToVid(voteId);
  }

  // Resolve a saeima_votes.id (vid) to a column and reveal it. If the vote is
  // older than the recent shard, pull the full archive and retry once.
  function scrollToVid(voteId) {
    for (var i = 0; i < DATA.votes.length; i++) {
      if (DATA.votes[i].vid === voteId) {
        revealVote(i);
        return;
      }
    }
    if (!fullLoaded && FULL_SRC) {
      ensureFullData(function () {
        renderShell();
        scrollToVid(voteId);
      });
    }
  }

  function revealVote(i) {
    // If vote is outside the current visible window, expand to full history.
    var visIdx = computeVisibleVoteIndices();
    if (visIdx.indexOf(i) < 0) {
      STATE.range = "all";
      STATE.confirmedAll = true;
      render();
    }
    setTimeout(function () {
      showVoteDetail(i);
      var header = document.querySelector(
        '.matrix-vote-header[data-vote-idx="' + i + '"]',
      );
      if (header) header.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    }, 50);
  }

  // ── Helpers ──────────────────────────────────────────────────────
  // saeima_votes.result vārdnīca NAV binārā. Bez "Pieņemts"/"Noraidīts"
  // avots lieto arī darbības etiķeti (piem. "Nod. kom." — nodots komisijām,
  // 2026-08-18), un tukšs lauks nozīmē, ka avots iznākumu nenosauc. Sarkans
  // abos gadījumos apgalvotu noraidījumu, kāda nav — tāpēc neitrāla nozīmīte.
  function resultBadgeClass(r) {
    if (r === "Pieņemts") return "badge-green";
    if (r === "Noraidīts") return "badge-red";
    return "badge-muted";
  }
  // Matricas kolonnas iznākuma punkts — TĀ PATI trīszaru vārdnīca, kas
  // resultBadgeClass. Nezināms iznākums paliek neitrāls; jaunu krāsu nozīmju
  // šeit nav.
  function resultDotClass(r) {
    if (r === "Pieņemts") return "is-pass";
    if (r === "Noraidīts") return "is-fail";
    return "is-other";
  }
  // Latviešu skaitļa saskaņojums: 1, 21, 31 … → vienskaitlis; 11 un pārējie →
  // daudzskaitlis. Bez šī "41 balsojumi" un "1 pieņemti" iet publiskā virsmā.
  function lvPlural(n, one, many) {
    return n % 10 === 1 && n % 100 !== 11 ? one : many;
  }
  // Frakcija balsoja nevienoti: vairākuma daļa < 80% pie vismaz 3 nodotām
  // balsīm. VIENA definīcija — kartītes `is-split` čips, TAB-1 "Tikai dalītie"
  // filtrs un matricas kopsavilkums to visi sauc, tāpēc tie nevar izšķirties.
  function factionIsSplit(fb) {
    var par = fb.p || 0,
      pret = fb.n || 0,
      att = fb.a || 0,
      nb = fb.x || 0;
    var total = par + pret + att + nb;
    if (total < 3) return false;
    var best = Math.max(par, pret, att, nb);
    return best / total < 0.8;
  }
  function voteIsSplit(v) {
    var fbs = v.f || [];
    for (var i = 0; i < fbs.length; i++) {
      if (factionIsSplit(fbs[i])) return true;
    }
    return false;
  }
  // Lasījuma stadija no motīva. Avota formulējumi: "2.lasījums" (biežākais),
  // "otrajam/trešajam lasījumam" (priekšlikumu balsojumi), "nodošana komisijām".
  // Atgriež TIKAI to, kas motīvā tiešām stāv — nekas netiek uzminēts.
  function readingStage(motif) {
    var m = motif || "";
    var num = m.match(/(\d)\.\s*lasījum/i);
    if (num) return num[1] + ".lasījums";
    if (/otrajam\s+lasījum/i.test(m)) return "2.lasījumam";
    if (/trešajam\s+lasījum/i.test(m)) return "3.lasījumam";
    if (/nodošana\s+komisij/i.test(m)) return "nodošana komisijām";
    return "";
  }
  function escHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
  function escAttr(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
  function lvDate(s) {
    if (!s || s.length < 10 || s.indexOf("-") === -1) return s || "";
    return s.substring(8, 10) + "." + s.substring(5, 7) + "." + s.substring(0, 4);
  }
  // Matricas kolonnai — dd.mm tekošajā gadā, dd.mm.gggg citos. Gads netiek
  // klusi noklusēts: ja tas nav šis gads, tas ir redzams.
  function shortDate(s, curYear) {
    if (!s || s.length < 10 || s.indexOf("-") === -1) return s || "";
    var dm = s.substring(8, 10) + "." + s.substring(5, 7);
    return s.substring(0, 4) === curYear ? dm : dm + "." + s.substring(0, 4);
  }
  function subtractDays(isoDate, days) {
    if (!isoDate || isoDate.length < 10) return "";
    var d = new Date(isoDate.substring(0, 10));
    if (isNaN(d.getTime())) return "";
    d.setUTCDate(d.getUTCDate() - days);
    var mm = String(d.getUTCMonth() + 1).padStart(2, "0");
    var dd = String(d.getUTCDate()).padStart(2, "0");
    return d.getUTCFullYear() + "-" + mm + "-" + dd;
  }

  // ══════════════════════════════════════════════════════════════════
  // TAB-1 "archive mode" — render vote-list cards from the matrix JSON so the
  // Balsojumi subtab can filter by ANY session/topic/deputy across the full
  // history (not just the SSR'd latest 200). Shares DATA + the recent/full
  // lazy-load with the matrix. Card markup mirrors templates/balsojumi.html.j2
  // so client-rendered archive cards match the SSR cards exactly.
  // Plan: docs/superpowers/plans/archive/2026-06-03-balsojumi-archive-filter.md
  // ══════════════════════════════════════════════════════════════════

  var _nameToPid = null; // lazy {politician name → pid} for the deputy filter
  function nameToPid() {
    if (_nameToPid) return _nameToPid;
    _nameToPid = {};
    if (DATA && DATA.politicians) {
      Object.keys(DATA.politicians).forEach(function (pid) {
        var p = DATA.politicians[pid];
        if (p && p.n) _nameToPid[p.n] = pid;
      });
    }
    return _nameToPid;
  }

  function csMap() {
    var m = {};
    (DATA.factions || []).forEach(function (f) {
      m[f.f] = f.cs || "other";
    });
    return m;
  }

  // Filter the full vote set by active TAB-1 selections → vote indices
  // newest-first. filters =
  //   {topics:[], deputies:[], sessions:[], months:[], q:"", splitOnly:false}.
  // q = free-text keyword search over motif + summary + document_nr; every
  // whitespace-separated term must match (AND), case-insensitive.
  // months = ["YYYY-MM"] — first level of the two-step session filter; applies
  // on its own, and ANDs with `sessions` when both are set.
  // splitOnly = keep only votes where some faction voted non-uniformly
  // (factionIsSplit — the SAME rule the card's `is-split` chip uses).
  function archiveFilterIndices(filters) {
    var votes = DATA.votes;
    var topics = filters.topics || [];
    var sessions = filters.sessions || [];
    var months = filters.months || [];
    var splitOnly = !!filters.splitOnly;
    var deputies = filters.deputies || [];
    var terms = (filters.q || "")
      .toLowerCase()
      .split(/\s+/)
      .filter(Boolean);
    var n2p = nameToPid();
    var depPids = deputies
      .map(function (nm) {
        return n2p[nm];
      })
      .filter(Boolean);
    var out = [];
    for (var i = 0; i < votes.length; i++) {
      var v = votes[i];
      if (topics.length && topics.indexOf(v.tp) < 0) continue;
      if (months.length && months.indexOf((v.d || "").substring(0, 7)) < 0) continue;
      if (sessions.length && sessions.indexOf(v.d) < 0) continue;
      if (splitOnly && !voteIsSplit(v)) continue;
      if (terms.length) {
        var hay = (v.m + " " + (v.s || "") + " " + (v.doc_nr || "")).toLowerCase();
        var allHit = true;
        for (var t = 0; t < terms.length; t++) {
          if (hay.indexOf(terms[t]) < 0) {
            allHit = false;
            break;
          }
        }
        if (!allHit) continue;
      }
      if (depPids.length) {
        var hit = false;
        for (var d = 0; d < depPids.length; d++) {
          var pol = DATA.politicians[depPids[d]];
          if (pol && pol.v.charAt(i) !== ".") {
            hit = true;
            break;
          }
        }
        if (!hit) continue;
      }
      out.push(i);
    }
    // Compact vote index is chronological ASC; reverse for newest-first display.
    out.sort(function (a, b) {
      return b - a;
    });
    return out;
  }

  // Tracked-politician rows for a vote: scan politicians for a cast vote at i.
  function trackedForVote(i) {
    var rows = [];
    var pols = DATA.politicians;
    for (var pid in pols) {
      if (!Object.prototype.hasOwnProperty.call(pols, pid)) continue;
      var p = pols[pid];
      var ch = p.v.charAt(i);
      if (ch && ch !== ".") rows.push({ name: p.n, faction: p.f, ch: ch, slug: p.s });
    }
    rows.sort(function (a, b) {
      return a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
    });
    return rows;
  }

  var _badgeForCh = { P: "badge-green", N: "badge-red", A: "badge-yellow" };

  // Build one SSR-identical vote card from compact vote index i.
  function archiveBuildCard(i, cs) {
    var v = DATA.votes[i];
    var tracked = trackedForVote(i);
    var depNames = tracked
      .map(function (t) {
        return t.name;
      })
      .join(",");
    var resultClass = resultBadgeClass(v.r);
    var h = [];
    h.push(
      '<div class="vote-card" id="vote-' +
        v.vid +
        '" data-topic="' +
        escAttr(v.tp) +
        '" data-date="' +
        escAttr(v.d) +
        '" data-result="' +
        escAttr(v.r) +
        '" data-deputies="' +
        escAttr(depNames) +
        '">',
    );
    // Konteksta rinda virs motīva. Motīvs "Par priekšlikumu Nr.1 … 2.lasījums"
    // bez dokumenta numura un stadijas nav saprotams; visi lauki jau ir JSON.
    // Iznākums te NETIEK atkārtots — tas ar pilniem skaitļiem stāv nozīmīšu
    // rindā tieši zemāk.
    var kicker = [];
    var docNr = v.doc_nr || v.bnr || "";
    if (docNr) kicker.push('<span class="vote-kicker-doc">' + escHtml(docNr) + "</span>");
    var stage = readingStage(v.m);
    if (stage) kicker.push("<span>" + escHtml(stage) + "</span>");
    if (/steidzam/i.test(v.m || "")) kicker.push("<span>steidzams</span>");
    // T14: viens likumprojekts = balsojumu ĶĒDE (darba kārtība, nodošana
    // komisijām, lasījumi, priekšlikumi), un frakcija ķēdē mēdz šķelties
    // procesa, ne satura dēļ. Saite aizved uz visiem šī dokumenta balsojumiem;
    // meklēšana jau skenē `doc_nr`, tāpēc jauns datu lauks nav vajadzīgs.
    if (v.doc_nr) {
      kicker.push(
        '<a href="#" class="vote-chain-link" data-doc-nr="' +
          escAttr(v.doc_nr) +
          '" title="Viens likumprojekts iziet vairākus balsojumus — atsevišķs procedurāls balsojums nav partijas pozīcija.">' +
          "visi šī dokumenta balsojumi &#8594;</a>",
      );
    }
    if (kicker.length) {
      h.push('<div class="vote-kicker">' + kicker.join('<span class="vote-kicker-sep">·</span>') + "</div>");
    }
    h.push('<div class="vote-header"><div class="vote-motif">' + escHtml(v.m) + "</div>");
    h.push(
      '<div class="vote-meta">' +
        escHtml(lvDate(v.d)) +
        (v.t ? " " + escHtml(v.t) : "") +
        "</div></div>",
    );
    h.push('<div class="vote-badges">');
    h.push(
      '<span class="badge ' +
        resultClass +
        '">' +
        escHtml(v.r) +
        "</span>",
    );
    h.push('<span class="badge badge-green">Par: ' + v.tot[0] + "</span>");
    h.push('<span class="badge badge-red">Pret: ' + v.tot[1] + "</span>");
    h.push('<span class="badge badge-yellow">Atturas: ' + v.tot[2] + "</span>");
    h.push("</div>");

    if (v.f && v.f.length) {
      h.push('<div class="faction-strip">');
      v.f.forEach(function (fb) {
        var par = fb.p || 0,
          pret = fb.n || 0,
          att = fb.a || 0,
          nb = fb.x || 0;
        var total = par + pret + att + nb;
        var counts = { Par: par, Pret: pret, Atturas: att, Nebalsoja: nb };
        var mv = null,
          best = -1;
        ["Par", "Pret", "Atturas", "Nebalsoja"].forEach(function (k) {
          if (counts[k] > best) {
            best = counts[k];
            mv = k;
          }
        });
        var discipline = total ? best / total : 0;
        var isSplit = total >= 3 && discipline < 0.8;
        var status = cs[fb.f] || "other";
        var cls = "faction-chip";
        if (status === "coalition") cls += " is-coalition";
        else if (status === "opposition") cls += " is-opposition";
        if (isSplit) cls += " is-split";
        var title =
          fb.f +
          ": par " +
          par +
          ", pret " +
          pret +
          ", atturas " +
          att +
          ", nebalsoja " +
          nb +
          (isSplit
            ? " — dalīts balsojums (" + Math.round(discipline * 100) + "% vienotība)"
            : "");
        h.push(
          '<span class="' +
            cls +
            '" title="' +
            escAttr(title) +
            '"><strong>' +
            escHtml(fb.f) +
            "</strong>",
        );
        if (isSplit) {
          if (par) h.push('<span class="chip-par">' + par + " par</span>");
          if (pret) h.push('<span class="chip-pret">' + pret + " pret</span>");
          if (att) h.push('<span class="chip-atturas">' + att + " att</span>");
          if (nb) h.push('<span class="chip-nebalso">' + nb + " nb</span>");
        } else if (mv === "Par") {
          h.push('<span class="chip-par">' + total + " par</span>");
        } else if (mv === "Pret") {
          h.push('<span class="chip-pret">' + total + " pret</span>");
        } else if (mv === "Atturas") {
          h.push('<span class="chip-atturas">' + total + " atturas</span>");
        } else if (mv === "Nebalsoja") {
          h.push('<span class="chip-nebalso">' + total + " nebalsoja</span>");
        }
        h.push("</span>");
      });
      h.push("</div>");
    }

    if (v.s) {
      h.push(
        '<div style="margin-top:0.75rem; font-size:0.9rem; color:var(--text-muted); line-height:1.6;">' +
          escHtml(v.s) +
          "</div>",
      );
      // Priekšlikumu balsojumi manto māsas 1. lasījuma kopsavilkumu (246 rindas;
      // operatora lēmums 2026-08-17/18: konvencija paliek, tekstu nepārraksta).
      // Lasītājam tas izskatās kā fakts par ŠO balsojumu, tāpēc to nosaucam.
      // Piezīme ir apgalvojums par datiem, nevis datu labojums.
      if (/^Par priekšlikumu/i.test(v.m || "")) {
        h.push(
          '<p class="vote-summary-caveat">Kopsavilkums apraksta likumprojekta virzību kopumā, ne tikai šo balsojumu.</p>',
        );
      }
    }

    var links = [];
    if (v.bsl)
      links.push(
        '<a href="likumprojekti/' +
          escAttr(v.bsl) +
          '.html">Likumprojekts' +
          (v.bnr ? " " + escHtml(v.bnr) : "") +
          "</a>",
      );
    if (v.doc_url)
      links.push(
        '<a href="' +
          escAttr(v.doc_url) +
          '" target="_blank" rel="noopener">titania.saeima.lv &#8599;</a>',
      );
    if (v.url)
      links.push(
        '<a href="' +
          escAttr(v.url) +
          '" target="_blank" rel="noopener">Balsojuma tabula &#8599;</a>',
      );
    if (links.length) {
      h.push(
        '<div style="margin-top:0.5rem; display:flex; gap:1rem; font-size:0.85rem;">' +
          links.join("") +
          "</div>",
      );
    }

    if (tracked.length) {
      h.push(
        '<details style="margin-top:0.5rem;"><summary style="cursor:pointer; font-size:0.85rem; color:var(--text-muted);">Izsekotie politiķi (' +
          tracked.length +
          ")</summary>",
      );
      h.push('<table style="margin-top:0.5rem; width:100%;">');
      tracked.forEach(function (t) {
        var label = VOTE_LABEL[t.ch] || t.ch;
        var bcls = _badgeForCh[t.ch] || "badge-muted";
        h.push(
          '<tr><td style="padding:0.2rem 0.5rem;"><a href="politiki/' +
            escAttr(t.slug) +
            '.html">' +
            escHtml(t.name) +
            "</a></td>",
        );
        h.push(
          '<td style="padding:0.2rem 0.5rem; color:var(--text-muted); font-size:0.85rem;">' +
            escHtml(t.faction) +
            "</td>",
        );
        h.push(
          '<td style="padding:0.2rem 0.5rem;"><span class="badge ' +
            bcls +
            '">' +
            escHtml(label) +
            "</span></td></tr>",
        );
      });
      h.push("</table></details>");
    }
    h.push("</div>");
    return h.join("");
  }

  // Public TAB-1 entry. Ensures the vote data is loaded, filters, then
  // returns card HTML for the first `limit` matches (newest-first) via cb.
  //   cb({ html, total, shown })  ·  errcb(msg)
  // opts.wantFull (default TRUE) picks the shard: false → recent shard only
  // (fast, ~1-year window); true → full archive. Newest-first ordering makes
  // the recent shard a prefix of the full one, so offsets stay valid when the
  // caller escalates from recent → full mid-pagination.
  // Sēdes dienas grupas virsraksts. `dayIdx` = VISI attiecīgās dienas indeksi
  // pašreizējā filtrētajā kopā, ne tikai šajā lapā redzamie — tāpēc skaitļi
  // nesarūk, kad diena pārdalās starp divām "Rādīt vairāk" lapām. Skaita tikai
  // eksplicītus Pieņemts/Noraidīts; pārējais nosaukts, nevis uzminēts (tā pati
  // vārdnīca, kas lapas galvenes metrikās).
  function archiveGroupHeader(dateStr, dayIdx) {
    var votes = DATA.votes;
    var accepted = 0;
    var rejected = 0;
    for (var i = 0; i < dayIdx.length; i++) {
      var r = votes[dayIdx[i]].r;
      if (r === "Pieņemts") accepted++;
      else if (r === "Noraidīts") rejected++;
    }
    var other = dayIdx.length - accepted - rejected;
    var parts = [
      dayIdx.length + " " + lvPlural(dayIdx.length, "balsojums", "balsojumi"),
    ];
    if (accepted) parts.push(accepted + " " + lvPlural(accepted, "pieņemts", "pieņemti"));
    if (rejected) parts.push(rejected + " " + lvPlural(rejected, "noraidīts", "noraidīti"));
    if (other) parts.push(other + " ar citu iznākumu");
    return (
      '<div class="vote-day-group" data-date="' +
      escAttr(dateStr) +
      '"><span class="vote-day-date">' +
      escHtml(lvDate(dateStr)) +
      '</span><span class="vote-day-counts">' +
      escHtml(parts.join(" · ")) +
      "</span></div>"
    );
  }

  window.balsojumiArchiveRender = function (recentSrc, fullSrc, filters, opts, cb, errcb) {
    RECENT_SRC = RECENT_SRC || recentSrc;
    FULL_SRC = FULL_SRC || fullSrc || recentSrc;
    var limit = (opts && opts.limit) || 200;
    var offset = (opts && opts.offset) || 0;
    var wantFull = !opts || opts.wantFull !== false;
    ensureData(
      wantFull,
      function () {
        var idx = archiveFilterIndices(filters);
        var cs = csMap();
        var slice = idx.slice(offset, offset + limit);
        // Sēžu dienu grupēšana: 40 vienas dienas kartītes plakanā lentē
        // izskatījās kā 40 neatkarīgi notikumi. Grupas skaitļus rēķina pār
        // VISU filtrēto kopu (dayCounts), bet virsrakstu izvada tikai tad, kad
        // diena tiešām sākas — `idx[offset-1]` pārbaude nozīmē, ka lapas robeža
        // dienas vidū NEDOD atkārtotu virsrakstu.
        var dayCounts = {};
        for (var d = 0; d < idx.length; d++) {
          var dk = DATA.votes[idx[d]].d;
          (dayCounts[dk] = dayCounts[dk] || []).push(idx[d]);
        }
        var prevDate =
          offset > 0 && idx[offset - 1] !== undefined
            ? DATA.votes[idx[offset - 1]].d
            : null;
        var out = [];
        for (var s = 0; s < slice.length; s++) {
          var vi = slice[s];
          var vd = DATA.votes[vi].d;
          if (vd !== prevDate) {
            out.push(archiveGroupHeader(vd, dayCounts[vd] || []));
            prevDate = vd;
          }
          out.push(archiveBuildCard(vi, cs));
        }
        cb({ html: out.join(""), total: idx.length, shown: offset + slice.length });
      },
      errcb || function () {},
    );
  };
})();
