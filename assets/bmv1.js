/*
 * Balsojumu saraksta renderētājs (balsojumi.html). Source: assets/bmv1.js →
 * copied to output/atmina/assets/bmv1.js.
 *
 * Fetches the compact vote JSON (src/render/votes_matrix.py::_build_matrix_compact:
 * data/balsojumi-matrica-recent.json — ~1-year shard — and, lazily,
 * data/balsojumi-matrica.json — the full archive) and renders the vote-list
 * cards client-side: window.balsojumiArchiveRender (cards + filters),
 * window.balsojumiVoteDate (#vote-N deep link → session day),
 * window.balsojumiTrackedHtml (tracked-politician table on first <details> open),
 * window.balsojumiSeatInfo (vid, pid → deputy behind a seat; popover in blv1.js).
 * Page init lives in assets/blv1.js.
 *
 * The deputy×vote "Matrica" tab was removed 2026-10-16
 * (docs/superpowers/plans/archive/2026-10-16-matrica-iznemsana.md); the JSON file
 * names keep "matrica" for cache/back-compat only.
 *
 * Vote-string encoding (matches meta.encoding field):
 *   P = Par, N = Pret, A = Atturas, X = Nebalsoja, '.' = nav individuālā ieraksta.
 */
(function () {
  "use strict";

  var DATA = null; // parsed JSON (recent shard by default; full archive once loaded)
  var RECENT_SRC = null; // recent-shard URL (default payload)
  var FULL_SRC = null; // full-archive URL, fetched lazily (any filter, "Rādīt vairāk" past the shard, deep link)
  var fullLoaded = false;

  var VOTE_LABEL = { P: "Par", N: "Pret", A: "Atturas", X: "Nebalsoja", ".": "Nav ieraksta" };

  // ── Shared data loader ───────────────────────────────────────────
  // Fetch+parse a JSON shard into DATA. markFull flags the full archive so
  // ensureData() knows the superset is present. cb(DATA) on success; errcb(msg)
  // on failure (the caller decides how to surface it).
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
        // Novēlota recent atbilde (piem. sākuma ielāde, kamēr lietotāja filtrs
        // jau ielādēja pilno arhīvu) NEDRĪKST pazemināt DATA: citādi
        // fullLoaded=true paliktu pie saīsinātajiem datiem, un vecas dienas
        // filtrs dotu 0. Izsaucējs saņem esošo pilno DATA.
        if (!markFull && fullLoaded) {
          cb(DATA);
          return;
        }
        DATA = json;
        _nameToPid = null; // cits shards — vārdu karte jāpārbūvē
        _vidToIdx = null; // … un vid → indekss (indeksi starp šķembām nesakrīt)
        if (markFull) fullLoaded = true;
        cb(DATA);
      })
      .catch(function (err) {
        (errcb || function () {})(
          err && err.message ? err.message : "nezināma kļūda",
        );
      });
  }

  // Unified data ensure for the vote list.
  //   wantFull=false → recent shard is enough (unfiltered default view, a
  //                    deep-link day inside the shard).
  //   wantFull=true  → must have the full archive (any filter that spans all
  //                    history, a deep-link day older than the shard).
  // Idempotent: returns the already-loaded DATA when it satisfies the request.
  function ensureData(wantFull, cb, errcb) {
    if (DATA && (!wantFull || fullLoaded)) {
      cb(DATA);
      return;
    }
    var src = wantFull ? FULL_SRC || RECENT_SRC : RECENT_SRC || FULL_SRC;
    loadInto(src, !!wantFull, cb, errcb);
  }

  // ── Helpers ──────────────────────────────────────────────────────
  // Kartītes iznākuma vārda klase. saeima_votes.result vārdnīca NAV binārā:
  // bez "Pieņemts"/"Noraidīts" avots lieto arī darbības etiķeti (piem.
  // "Nod. kom." — nodots komisijām, 2026-08-18), un tukšs lauks nozīmē, ka
  // avots iznākumu nenosauc. Sarkans abos gadījumos apgalvotu noraidījumu,
  // kāda nav — tāpēc trešais, neitrālais zars (sargā
  // tests/test_balsojumi_readability.py::test_unknown_result_never_renders_a_red_badge).
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
  // Balsojuma sadalījuma grupa deputātiem bez frakcijas (NULL/''). Tā pati
  // etiķete kā src/render/votes_matrix.py::NO_FACTION_LABEL — to sargā
  // tests/test_votes_no_faction_bucket.py.
  var NO_FACTION = "ārpusfrakciju";
  // Frakcija balsoja nevienoti: vairākuma daļa < 80% pie vismaz 3 nodotām
  // balsīm. VIENA definīcija — kartītes `is-split` čips un "Tikai dalītie"
  // filtrs to abi sauc, tāpēc tie nevar izšķirties.
  // Ārpusfrakciju deputāti nav grupa, kas varētu "sašķelties" — nekad dalīts.
  function factionIsSplit(fb) {
    if (fb.f === NO_FACTION) return false;
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
  // Redzamais datums DD.MM.YYYY — kopīgais window.atminaLvDate (assets/sgv1.js).
  // Šis fails ir sinhrons, sgv1 — `defer`; lvDate tiek saukts tikai datu
  // ielādes atzvanos (pēc fetch), kad sgv1 jau ir izpildīts. Aizsargs atstāj
  // tekstu kā ir, ja tā tomēr vēl nav.
  function lvDate(s) {
    return window.atminaLvDate ? window.atminaLvDate(s) : (s == null ? "" : String(s));
  }

  // ══════════════════════════════════════════════════════════════════
  // Vote-list cards from the compact JSON, so the list can filter by ANY
  // session/topic/deputy across the full history. The cards are the ONLY
  // rendering path (no SSR cards since 2026-07-17).
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

  // Filter the full vote set by active list selections → vote indices
  // newest-first. filters =
  //   {topics:[], deputies:[], sessions:[], months:[], q:"", splitOnly:false}.
  // q = free-text keyword search over motif + summary + document_nr; every
  // whitespace-separated term must match (AND), case- and diacritic-insensitive
  // ("izglitiba" finds "Izglītības").
  // months = ["YYYY-MM"] — first level of the two-step session filter; applies
  // on its own, and ANDs with `sessions` when both are set.
  // splitOnly = keep only votes where some faction voted non-uniformly
  // (factionIsSplit — the SAME rule the card's `is-split` chip uses).
  function foldText(s) {
    return String(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }

  function archiveFilterIndices(filters) {
    var votes = DATA.votes;
    var topics = filters.topics || [];
    var sessions = filters.sessions || [];
    var months = filters.months || [];
    var splitOnly = !!filters.splitOnly;
    var deputies = filters.deputies || [];
    var terms = foldText(filters.q || "")
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
        // Folded once per vote and cached on it — search runs on every keystroke.
        var hay = v._hay || (v._hay = foldText(v.m + " " + (v.s || "") + " " + (v.doc_nr || "")));
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

  // Deputāta frakcija PIE balsojuma i (T6 corollary): `fr` = [[startIdx,
  // "FRAKCIJA"], …] indeksēts kā `v` (votes_matrix.py). Bez `fr` (vecs JSON)
  // vai pirms pirmā ieraksta — `p.f` (jaunākā frakcija).
  function factionAt(p, i) {
    var fr = p.fr;
    if (!fr || !fr.length) return p.f;
    var f = p.f;
    for (var k = 0; k < fr.length && fr[k][0] <= i; k++) f = fr[k][1];
    return f;
  }

  // Profila saite tikai tiem, kam profils ir (`pp`), citādi vārds kā teksts.
  function nameHtml(slug, name, pp) {
    if (!pp) return escHtml(name);
    return '<a href="politiki/' + escAttr(slug) + '.html">' + escHtml(name) + "</a>";
  }

  // Frakcijas etiķete lasītājam: grupas atslēga «ārpusfrakciju» viena pati nav
  // teikums, tāpēc rāda «ārpus frakcijām». Atslēga (kārtošana, grupas) nemainās.
  function factionLabel(f) {
    return f === NO_FACTION ? "ārpus frakcijām" : f;
  }

  // Kārtošana latviski (Ā pie A, ne aiz Z). Tie paši komparatori zālei,
  // frakciju joslām un saraksta pogām «Pēc vārda / frakcijas / balss».
  var _coll = window.Intl && Intl.Collator ? new Intl.Collator("lv") : null;
  function cmpText(a, b) {
    a = a || "";
    b = b || "";
    return _coll ? _coll.compare(a, b) : a < b ? -1 : a > b ? 1 : 0;
  }
  function byName(a, b) {
    return cmpText(a.name, b.name);
  }
  // Frakcija pie balsojuma, ārpusfrakciju pēdējie; tad vārds.
  function byFaction(a, b) {
    var na = a.faction === NO_FACTION,
      nb = b.faction === NO_FACTION;
    if (na !== nb) return na ? 1 : -1;
    return cmpText(a.faction, b.faction) || byName(a, b);
  }
  var BALLOT_ORDER = { P: 0, N: 1, A: 2, X: 3 };
  function byBallot(a, b) {
    return BALLOT_ORDER[a.ch] - BALLOT_ORDER[b.ch] || byName(a, b);
  }

  // vid → indekss PAŠREIZĒJĀ DATA (atiestata loadInto pie šķembas maiņas).
  var _vidToIdx = null;
  function voteIndex(vid) {
    if (!DATA) return -1;
    if (!_vidToIdx) {
      _vidToIdx = {};
      for (var k = 0; k < DATA.votes.length; k++) _vidToIdx[DATA.votes[k].vid] = k;
    }
    var i = _vidToIdx[vid];
    return i === undefined ? -1 : i;
  }

  // Tracked-politician rows for a vote: scan politicians for a cast vote at i.
  function trackedForVote(i) {
    var rows = [];
    var pols = DATA.politicians;
    for (var pid in pols) {
      if (!Object.prototype.hasOwnProperty.call(pols, pid)) continue;
      var p = pols[pid];
      var ch = p.v.charAt(i);
      if (ch && ch !== ".")
        rows.push({ pid: pid, name: p.n, faction: factionAt(p, i), ch: ch, slug: p.s, pp: p.pp });
    }
    rows.sort(byName);
    return rows;
  }

  var _badgeForCh = { P: "badge-green", N: "badge-red", A: "badge-yellow" };

  // Izsekoto politiķu tabula vienam balsojumam (vid → indekss PAŠREIZĒJĀ
  // DATA) ar kārtošanas pogām. Rindas nāk vārdu secībā; katra nes savu vietu
  // trijos kārtojumos (data-o-*), tāpēc blv1.js tikai pārliek <tbody> rindas —
  // pogas netiek pārrakstītas, fokuss paliek uz nospiestās.
  function trackedTableHtml(vid) {
    var i = voteIndex(Number(vid));
    if (i < 0) return "";
    var rows = trackedForVote(i);
    var rank = function (cmp) {
      var r = {};
      rows
        .slice()
        .sort(cmp)
        .forEach(function (t, k) {
          r[t.pid] = k;
        });
      return r;
    };
    var rf = rank(byFaction),
      rb = rank(byBallot);
    var h = [
      '<div class="vote-sort" role="group" aria-label="Kārtot sarakstu">' +
        '<span class="vote-sort-label" aria-hidden="true">Kārtot:</span>' +
        '<button type="button" class="chip vote-sort-btn" data-sort="name" aria-pressed="true">Pēc vārda</button>' +
        '<button type="button" class="chip vote-sort-btn" data-sort="faction" aria-pressed="false">Pēc frakcijas</button>' +
        '<button type="button" class="chip vote-sort-btn" data-sort="ballot" aria-pressed="false">Pēc balss</button>' +
        "</div>",
      '<table style="margin-top:0.5rem; width:100%;"><tbody>',
    ];
    rows.forEach(function (t, k) {
      var label = VOTE_LABEL[t.ch] || t.ch;
      var bcls = _badgeForCh[t.ch] || "badge-muted";
      h.push(
        '<tr data-o-name="' + k + '" data-o-faction="' + rf[t.pid] + '" data-o-ballot="' +
          rb[t.pid] + '"><td style="padding:0.2rem 0.5rem;">' +
          nameHtml(t.slug, t.name, t.pp) + "</td>",
      );
      h.push(
        '<td style="padding:0.2rem 0.5rem; color:var(--text-muted); font-size:0.85rem;">' +
          escHtml(factionLabel(t.faction)) +
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
    h.push("</tbody></table>");
    return h.join("");
  }
  window.balsojumiTrackedHtml = trackedTableHtml;

  // Deputāts aiz zāles/frakcijas kvadrātiņa (blv1.js lodziņš). Atslēga ir vid,
  // ne indekss: recent→full ielāde nomaina DATA un nobīda indeksus.
  window.balsojumiSeatInfo = function (vid, pid) {
    var i = voteIndex(Number(vid));
    var p = DATA && DATA.politicians[pid];
    if (i < 0 || !p) return null;
    var ch = p.v.charAt(i);
    if (!ch || ch === ".") return null;
    return {
      name: p.n,
      faction: factionLabel(factionAt(p, i)),
      ballot: VOTE_LABEL[ch] || ch,
      profileUrl: p.pp ? "politiki/" + p.s + ".html" : null,
    };
  };

  // Izvēlēto deputātu balsis kartītē (deputātu filtrs). `.` = šim balsojumam
  // nav individuālā ieraksta — tas NAV «nepiedalījās», tāpēc VOTE_LABEL["."]
  // te netiek lietots.
  function selectedVotesHtml(i, selPids) {
    var rows = [];
    for (var d = 0; d < selPids.length; d++) {
      var p = DATA.politicians[selPids[d]];
      if (!p) continue;
      var ch = p.v.charAt(i);
      var vote =
        !ch || ch === "."
          ? '<span class="vote-selected-none">nav individuālā ieraksta</span>'
          : '<span class="badge ' +
            (_badgeForCh[ch] || "badge-muted") +
            '">' +
            escHtml(VOTE_LABEL[ch] || ch) +
            "</span>";
      // Ar balsi — frakcija pie TĀ balsojuma; bez ieraksta (`.`) balsojuma
      // frakcijas nav, tāpēc deputāta jaunākā (`p.f`).
      rows.push(
        '<span class="vote-selected-row">' +
          nameHtml(p.s, p.n, p.pp) +
          ' <span class="vote-selected-faction">' +
          escHtml(factionLabel(!ch || ch === "." ? p.f : factionAt(p, i))) +
          "</span> " +
          vote +
          "</span>",
      );
    }
    return rows.length ? '<div class="vote-selected">' + rows.join("") + "</div>" : "";
  }

  // Vietu josla: viens <i> uz deputāta vietu, secībā Par, Pret, Atturas,
  // Nebalsoja, tad `empty` tukšas vietas. cls = "vote-seat" (zāle) vai
  // "vote-mseat" (frakcijas mini josla). Krāsas — tikai tēmas žetoni (style.css).
  // by = {P:[pid…], N:…, A:…, X:…} jau vajadzīgajā secībā: k-tā vieta grupā
  // nes data-p = k-tais deputāts (lodziņš blv1.js). Ja individuālo ierakstu
  // ir mazāk par skaitu, atlikušās vietas paliek bez data-p; tukšās — vienmēr.
  function seatsHtml(cls, p, n, a, x, empty, by) {
    var h = [];
    var runs = [["vs-p", p, "P"], ["vs-n", n, "N"], ["vs-a", a, "A"], ["vs-x", x, "X"], ["vs-e", empty || 0, ""]];
    for (var r = 0; r < runs.length; r++) {
      var pids = (by && by[runs[r][2]]) || [];
      for (var k = 0; k < runs[r][1]; k++) {
        h.push(
          '<i class="' + cls + " " + runs[r][0] + '"' +
            (pids[k] ? ' data-p="' + escAttr(pids[k]) + '"' : "") + "></i>",
        );
      }
    }
    return h.join("");
  }

  // Rindas → {P:[pid…], N:[…], A:[…], X:[…]}, saglabājot rindu secību.
  function pidsByBallot(rows) {
    var by = { P: [], N: [], A: [], X: [] };
    rows.forEach(function (t) {
      if (by[t.ch]) by[t.ch].push(t.pid);
    });
    return by;
  }

  // Viena frakcijas rinda kartītē. Rāda VISUS nenulles skaitus ar vārdu
  // (vecais čips rādīja vairākumu + mazākumu — tie paši skaitļi), «dalīti» zīmi
  // pēc factionIsSplit (tā pati definīcija, ko filtrs «Tikai dalītie») un pilno
  // `title` tekstu nemainītu.
  // rows = šī balsojuma deputāti, kuru frakcija PIE balsojuma ir fb.f (T6) —
  // vārdu secībā; no tiem kvadrātiņu data-p.
  function factionRowHtml(fb, rows) {
    var par = fb.p || 0,
      pret = fb.n || 0,
      att = fb.a || 0,
      nb = fb.x || 0;
    var total = par + pret + att + nb;
    var best = Math.max(par, pret, att, nb);
    var discipline = total ? best / total : 0;
    var isSplit = factionIsSplit(fb);
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
    var counts = [];
    if (par) counts.push('<span class="vc-p">' + par + " par</span>");
    if (pret) counts.push('<span class="vc-n">' + pret + " pret</span>");
    if (att) counts.push('<span class="vc-a">' + att + " atturas</span>");
    if (nb) counts.push('<span class="vc-x">' + nb + " nebalsoja</span>");
    if (isSplit) counts.push('<span class="vote-faction-split">dalīti</span>');
    return (
      // `title` uz nosaukuma, ne visas rindas: kvadrātiņiem ir savs lodziņš
      // (#seat-pop), pārlūka padoms tam pāri traucētu.
      '<div class="vote-frow"><span class="vote-fname" title="' +
      escAttr(title) +
      '">' +
      escHtml(fb.f === NO_FACTION ? "ārpus" : fb.f) +
      '</span><span class="vote-fseats" aria-hidden="true">' +
      seatsHtml("vote-mseat", par, pret, att, nb, 0, pidsByBallot(rows || [])) +
      '</span><span class="vote-fcount">' +
      counts.join("") +
      "</span></div>"
    );
  }

  // Build one vote card from compact vote index i (dizains: operatora
  // apstiprinātais makets 2026-10-16). Neviens vecās kartītes fakts nav zudis —
  // tests/test_balsojumi_readability.py::test_card_redesign_loses_no_data.
  function archiveBuildCard(i, selPids) {
    var v = DATA.votes[i];
    var tracked = trackedForVote(i);
    // Kvadrātiņu deputāti: zālē balss grupā frakcija pie balsojuma, tad vārds;
    // frakcijas joslā — vārds. No tām pašām rindām, bez atkārtotas skenēšanas.
    var chamberBy = pidsByBallot(tracked.slice().sort(byFaction));
    var rowsByFaction = {};
    tracked.forEach(function (t) {
      (rowsByFaction[t.faction] = rowsByFaction[t.faction] || []).push(t);
    });
    var frow = function (fb) {
      return factionRowHtml(fb, rowsByFaction[fb.f]);
    };
    var depNames = tracked
      .map(function (t) {
        return t.name;
      })
      .join(",");
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
    // Augšējā rinda: dokuments + stadija + steidzams kreisajā pusē, datums ar
    // laiku labajā. Motīvs "Par priekšlikumu Nr.1 … 2.lasījums" bez dokumenta
    // numura un stadijas nav saprotams; visi lauki jau ir JSON.
    var kicker = [];
    var docNr = v.doc_nr || v.bnr || "";
    if (docNr) kicker.push('<span class="vote-kicker-doc">' + escHtml(docNr) + "</span>");
    var stage = readingStage(v.m);
    if (stage) kicker.push("<span>" + escHtml(stage) + "</span>");
    if (/steidzam/i.test(v.m || "")) kicker.push("<span>steidzams</span>");
    h.push(
      '<div class="vote-top"><div class="vote-kicker">' +
        kicker.join("") +
        '</div><time class="vote-time" datetime="' +
        escAttr(v.d) +
        '">' +
        escHtml(lvDate(v.d)) +
        (v.t ? ", " + escHtml(v.t) : "") +
        "</time></div>",
    );
    h.push('<h3 class="vote-title">' + escHtml(v.m) + "</h3>");

    // Iznākums: trīszaru vārdnīca (resultDotClass)
    // — zaļš tikai Pieņemts, sarkans tikai Noraidīts, pārējais neitrāls.
    var fbs = v.f || [];
    var P = v.tot[0] || 0,
      N = v.tot[1] || 0,
      A = v.tot[2] || 0,
      X = 0;
    fbs.forEach(function (fb) {
      X += fb.x || 0;
    });
    h.push(
      '<div class="vote-result"><span class="vote-result-word ' +
        resultDotClass(v.r) +
        '">' +
        escHtml(v.r || "Iznākums nav norādīts") +
        '</span><span class="vote-result-nums">' +
        '<span><b class="vc-p">' + P + "</b> par</span>" +
        '<span><b class="vc-n">' + N + "</b> pret</span>" +
        '<span><b class="vc-a">' + A + "</b> atturas</span>" +
        '<span><b class="vc-x">' + X + "</b> nebalsoja</span>" +
        "</span></div>",
    );
    if (selPids && selPids.length) h.push(selectedVotesHtml(i, selPids));

    // Zāles josla: 100 vietas; ja ierakstu ir vairāk par 100, rāda visus.
    var empty = Math.max(0, 100 - P - N - A - X);
    h.push(
      '<div class="vote-chamber" role="img" aria-label="' +
        escAttr(
          "Par " + P + ", pret " + N + ", atturas " + A + ", nebalsoja " + X + ", bez ieraksta " + empty,
        ) +
        '">' +
        seatsHtml("vote-seat", P, N, A, X, empty, chamberBy) +
        "</div>",
    );

    // Frakcijas divās kolonnās: koalīcija | opozīcija + ārpus frakcijām.
    // Koalīcija = valdība BALSOJUMA brīdī (DATA.coalitions[v.co]), ne šodienas
    // DATA.factions[].cs — Siliņas laikā PRO bija koalīcijā, AS opozīcijā.
    // v.co == null (pirms pirmā zināmā perioda) → viena grupa «Frakcijas».
    var coalition = v.co != null && DATA.coalitions ? DATA.coalitions[v.co] : null;
    if (fbs.length && !coalition) {
      h.push(
        '<div class="vote-factions"><div class="vote-fcol"><div class="vote-fgroup">' +
          '<div class="vote-fglabel">Frakcijas</div>' +
          fbs.map(frow).join("") +
          "</div></div></div>",
      );
    } else if (fbs.length) {
      var groups = { coalition: [], opposition: [], other: [] };
      fbs.forEach(function (fb) {
        var st =
          fb.f === NO_FACTION ? "other" : coalition.indexOf(fb.f) >= 0 ? "coalition" : "opposition";
        groups[st].push(fb);
      });
      var grp = function (key, label) {
        if (!groups[key].length) return "";
        return (
          '<div class="vote-fgroup"><div class="vote-fglabel">' +
          label +
          "</div>" +
          groups[key].map(frow).join("") +
          "</div>"
        );
      };
      h.push(
        '<div class="vote-factions"><div class="vote-fcol">' +
          grp("coalition", "Koalīcija") +
          '</div><div class="vote-fcol">' +
          grp("opposition", "Opozīcija") +
          grp("other", "Ārpus frakcijām") +
          "</div></div>",
      );
    }

    if (v.s) {
      h.push('<p class="vote-summary">' + escHtml(v.s) + "</p>");
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
    // T14: viens likumprojekts = balsojumu ĶĒDE (darba kārtība, nodošana
    // komisijām, lasījumi, priekšlikumi), un frakcija ķēdē mēdz šķelties
    // procesa, ne satura dēļ. Saite aizved uz visiem šī dokumenta balsojumiem
    // (blv1.js klausās `.vote-chain-link` + data-doc-nr).
    if (v.doc_nr)
      links.push(
        '<a href="#" class="vote-chain-link" data-doc-nr="' +
          escAttr(v.doc_nr) +
          '" title="Viens likumprojekts iziet vairākus balsojumus — atsevišķs procedurāls balsojums nav partijas pozīcija.">' +
          "Visi šī dokumenta balsojumi</a>",
      );

    // Slinkais saraksts (plāns 2026-10-16): kartītē tikai kopsavilkums ar
    // skaitu; tabulu ielej blv1.js `toggle` klausītājs pirmajā atvēršanā no
    // balsojumiTrackedHtml(vid) — tās pašas trackedForVote rindas. Atslēga ir
    // vid, ne indekss: recent→full eskalācija nomaina DATA, un indeksi starp
    // šardiem nesakrīt.
    var who = tracked.length
      ? '<details class="vote-tracked" data-vid="' +
        escAttr(v.vid) +
        '"><summary class="vote-who">Kā balsoja katrs deputāts <span class="vote-who-n">(' +
        tracked.length +
        ")</span></summary></details>"
      : "";
    if (links.length || who) {
      h.push(
        '<div class="vote-foot"><nav class="vote-links" aria-label="Saites">' +
          links.join("") +
          "</nav>" +
          who +
          "</div>",
      );
    }
    h.push("</div>");
    return h.join("");
  }

  // Public list entry. Ensures the vote data is loaded, filters, then
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

  // Balsojuma sēdes datums dziļajai saitei `balsojumi.html#vote-N`: saraksts,
  // kuram mērķis nav pirmajā renderā, ar to uzliek dienas filtru. Meklē
  // ielādētajā DATA; ja nav un pilnais arhīvs vēl nav ielādēts — ielādē to un
  // meklē vēlreiz. cb(null) TIKAI pēc veiksmīgas pilnā arhīva pārbaudes;
  // ielādes kļūda → errcb(msg) (tā nav «nav atrasts»).
  // Sauc pēc balsojumiArchiveRender, kas uzstāda RECENT_SRC/FULL_SRC.
  window.balsojumiVoteDate = function (vid, cb, errcb) {
    function find() {
      var votes = DATA.votes;
      for (var i = votes.length - 1; i >= 0; i--) {
        if (votes[i].vid === vid) return votes[i].d || null;
      }
      return null;
    }
    ensureData(
      false,
      function () {
        var d = find();
        if (d || fullLoaded) {
          cb(d);
          return;
        }
        ensureData(
          true,
          function () {
            cb(find());
          },
          errcb,
        );
      },
      errcb,
    );
  };

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
        var n2p = nameToPid();
        var selPids = ((filters && filters.deputies) || [])
          .map(function (nm) {
            return n2p[nm];
          })
          .filter(Boolean);
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
          out.push(archiveBuildCard(vi, selPids));
        }
        cb({ html: out.join(""), total: idx.length, shown: offset + slice.length });
      },
      errcb || function () {},
    );
  };
})();
