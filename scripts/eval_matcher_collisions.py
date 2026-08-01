"""Matcher-collision evaluation harness — READ-ONLY, repeatable.

Measures the CURRENT matcher's precision/coverage against two ground-truth
sets, then re-measures under candidate guard variants WITHOUT touching
src/matcher.py (each variant is a local re-implementation toggle):

  FP corpus  — 32 known false-link (pid, doc) pairs assembled from BACKLOG.md
               (§ Bērziņš false-link, § Kučinskis bare-surname) and the
               deleted-junction fix/rollback files in data/*.sql. Each row
               cites its provenance. These are documented, operator-confirmed
               mistakes — the harness asks "does variant X still link them?"
  GOLD corpus — every DISTINCT (opponent_id, document_id) pair backed by a
               stored claim (claim_type position/commentary, document_id NOT
               NULL). A claim means an extraction agent read the doc and
               confirmed the politician genuinely appears — the strongest
               true-link evidence we have. The harness asks "does variant X
               still find them?" (lost pair = silently lost coverage).
  SILVER sample — random junction docs, for churn estimates outside the
               claim-backed lane (mentions).
  TITLE corpus — docs whose title is NOT a substring of content; used only
               for the title-scan measurement (BACKLOG b6).

Variants (composable):
  boundary  (D) — a form occurrence only counts when both neighbours are
                  non-letters. Targets prefix bombs: "Kolu"→Kolumbija,
                  "Baško"→Baškortostāna, "Lāci"→Lācis.
  fn_all    (B) — the existing foreign-first-name veto (matcher.py, gated on
                  count==1) also fires when count>1 but NO matched form
                  contains the first name. Targets declined-namesake docs:
                  "Alberts Šmits ... Šmita līgums" matches 2 forms and today
                  bypasses the veto entirely.
  fn_particle   — with fn_all: when the word before the surname is a foreign
                  name particle ("del", "van", ...), test the word before it.
                  Targets "Isaks del Toro".
  domain=1/2 (A) — doc-level sports/culture lexicon guard: if >=2 distinct
                  domain stems and 0 politics stems, drop candidates whose
                  matched forms lack the first name (1) or ALL candidates (2).
                  Level 2 is the only string-level idea that can touch the
                  full-name-twin class (Andris Bērziņš).
  title     (T) — scan title + content instead of content only.
  strip_negs    — counterfactual: empty negative_patterns for FP-corpus pids,
                  to ask "would the code variant have prevented what the
                  operator later had to patch by hand?"

Fidelity: since the 2026-07-27 B2+D2+H package shipped in src/matcher.py, the
REAL matcher implements the B2D2H variant — the fidelity gate therefore runs
the B2D2H cfg against src.matcher.match_politicians() and aborts on any
divergence. The default cfg ("base") is a frozen re-implementation of the
PRE-package matcher, kept as the comparison baseline for gold-lost /
silver-removed / silver-added deltas. Shared veto lexicons and helpers are
imported from src.matcher so the two cannot drift apart silently.

Regression gates for the shipped package (docs/plans/2026-07-27 § 5.4,
re-derived at ship time): B2D2H fp_links ≤ 3 and gold_hit ≥ 1260.
NOTE 2026-07-27: the plan's original gold gate was 1262, measured with a
blanket "any sentence-initial capital is orthography" forgiveness. That rule
reopens the "Linda Abu Meri" class (a foreign FULL NAME opening a sentence
reads as orthography too) — invisible to the original harness because
variant-ADDED links went unreported; silver_added closes that blind spot.
The shipped B2 uses the closed-class _VETO_STOP_WORDS set instead, which
keeps every measured recovery except two docs whose only rescue token is an
open-class noun ("Vēlēšanās Šuvajevs", "Prokuratūra Stendzeniekam" — the
plan § 7.3 acknowledged out-of-scope class). Net coverage stays positive:
1260 = base 1258 − 3 (source typo + those two) + 5 (H handle recoveries).

Usage (from repo root; ALWAYS the project venv):
    .venv/Scripts/python.exe scripts/eval_matcher_collisions.py [--quick] [--out PATH]

Writes a JSON report (default data/eval_matcher_collisions.json is NOT used —
default goes to stdout dir eval_matcher_out.json) and prints an ASCII summary.
The DB is opened mode=ro; nothing is written to the database.
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import src.matcher as M  # noqa: E402
from src.matcher import (  # noqa: E402
    _NAME_PARTICLES,
    _ROLE_WORDS,
    _SENT_END,
    _VETO_STOP_WORDS,
    _clear_politician_cache,
    _first_token_decls,
    _latvian_surname_inflections,
    _load_politician_forms,
    _surname_has_person_context,
    extract_twitter_author_handle,
    match_politicians,
)

# ---------------------------------------------------------------------------
# FP corpus. Provenance per row:
#   BACKLOG = BACKLOG.md § Bērziņš false-link; slēgtā "Kučinskis bare-surname"
#             vēsture: wiki/CHANGELOG-arhivs.md § 2026-08-01 BACKLOG konsolidācija
#   sql:X   = data/X (fix or rollback file that deleted/re-inserted the row)
# klase: prefix (substring bomb), namesake (same surname, different first
# name present), fullname (full name coincides — negative_patterns can't
# help), commonword (surname is a common word), firstform (bare first-name
# form matched someone else's text).
FP_CASES: list[dict] = [
    dict(pid=24, doc=55385, klase="prefix", label="Kols-Kolumbus", src="sql:fix_audit_integrity_falsejunctions_2026-07-07.sql"),
    dict(pid=24, doc=57409, klase="prefix", label="Kols-Kolumbijas", src="sql:fix_audit_integrity_falsejunctions_2026-07-07.sql"),
    dict(pid=24, doc=61481, klase="prefix", label="Kols-Kolumbus", src="sql:fix_audit_integrity_falsejunctions_2026-07-07.sql"),
    dict(pid=24, doc=63856, klase="prefix", label="Kols-Kolumbus", src="sql:fix_audit_integrity_falsejunctions_2026-07-07.sql"),
    dict(pid=24, doc=60377, klase="prefix", label="Kols-Kolumbija", src="sql:fix_kols_kolumbija_negpattern_2026-06-29.sql"),
    dict(pid=24, doc=26483, klase="namesake", label="Kols-Allens", src="atmiņa 2026-04-26"),
    dict(pid=24, doc=26473, klase="namesake", label="Kols-Allens", src="atmiņa 2026-04-26"),
    dict(pid=30, doc=58027, klase="prefix", label="Basko-Baskortostana", src="sql:fix_basko_baskortostana_negpattern_2026-07-16.sql"),
    dict(pid=30, doc=68280, klase="prefix", label="Basko-Baskortostana", src="BACKLOG 2026-07-14"),
    dict(pid=30, doc=68740, klase="prefix", label="Basko-Baskortostana", src="BACKLOG 2026-07-16"),
    dict(pid=162, doc=72454, klase="namesake", label="Cudars-Matiss", src="sql:fix_cudars_matiss_negpattern_2026-07-24.sql"),
    dict(pid=132, doc=50837, klase="namesake", label="Skrastins-aktieris", src="sql:rollback_matcher_fp_patterns_2026-06-11.sql"),
    dict(pid=203, doc=51391, klase="commonword", label="Cerins-iela", src="sql:rollback_matcher_fp_patterns_2026-06-11.sql"),
    dict(pid=203, doc=51398, klase="commonword", label="Cerins-iela", src="sql:rollback_matcher_fp_patterns_2026-06-11.sql"),
    dict(pid=92, doc=50883, klase="firstform", label="Ivanovs-Volfsons", src="sql:rollback_matcher_fp_patterns_2026-06-11.sql"),
    dict(pid=83, doc=50893, klase="commonword", label="Daudze-daudzi", src="sql:rollback_matcher_fp_patterns_2026-06-11.sql"),
    dict(pid=124, doc=54315, klase="fullname", label="Salimovs-NGO", src="sql:fix_salimovs_homonym_2026-06-14.sql"),
    dict(pid=154, doc=52304, klase="namesake", label="Krauze-dirigents", src="sql:fix_krauze_negative_patterns_2026-06-12.sql"),
    dict(pid=158, doc=55276, klase="prefix", label="Lace-Lacis", src="sql:fix_audit_integrity_falsejunctions_2026-07-07.sql"),
    dict(pid=158, doc=60387, klase="prefix", label="Lace-Lacis", src="sql:fix_audit_integrity_falsejunctions_2026-07-07.sql"),
    dict(pid=158, doc=60396, klase="prefix", label="Lace-Lacis", src="sql:fix_audit_integrity_falsejunctions_2026-07-07.sql"),
    dict(pid=158, doc=63011, klase="prefix", label="Lace-Lacis", src="sql:fix_audit_integrity_falsejunctions_2026-07-07.sql"),
    dict(pid=158, doc=63862, klase="prefix", label="Lace-Lacis", src="sql:fix_audit_integrity_falsejunctions_2026-07-07.sql"),
    dict(pid=146, doc=62139, klase="fullname", label="Berzins-celu-buvetajs", src="BACKLOG 2026-07-02"),
    dict(pid=146, doc=64681, klase="fullname", label="Berzins-dziedatajs", src="BACKLOG 2026-07-08 (doc atrasts 07-27)"),
    dict(pid=146, doc=74402, klase="fullname", label="Berzins-aktieris", src="BACKLOG 2026-07-26"),
    dict(pid=105, doc=56077, klase="namesake", label="Kucinskis-Matiss", src="BACKLOG 2026-06-18 (doc atrasts 07-27)"),
    dict(pid=25, doc=62152, klase="namesake", label="Valainis-Oskars", src="BACKLOG 2026-07-02"),
    dict(pid=150, doc=68721, klase="namesake", label="Smits-Alberts", src="BACKLOG 2026-07-16"),
    dict(pid=150, doc=69330, klase="namesake", label="Smits-Rolands", src="BACKLOG 2026-07-16"),
    dict(pid=233, doc=74370, klase="namesake", label="Citskovskis-Ugis", src="BACKLOG 2026-07-26"),
    dict(pid=234, doc=74357, klase="namesake", label="Toro-del-Toro", src="BACKLOG 2026-07-26"),
]

# ---------------------------------------------------------------------------
# Variant A lexicons (doc-level, lowercase stem substrings). These are
# EVALUATION heuristics, not production values — the point is to measure the
# ceiling/floor of the approach, not to ship these lists.
LEX_DOMAIN = [
    # sports
    "čempion", "hokej", "basketbol", "futbol", "volejbol", "riteņbrauc",
    "vieglatlēt", "sacensīb", "sportist", "trener", "spēlētāj", "olimpisk",
    "turnīr", "pusfināl", "nhl", "nba", "atlēt",
    # kultūra / izklaide
    "koncert", "teātr", "izrād", "aktier", "aktris", "dziedātāj",
    "komponist", "diriģent", "festivāl", "režisor", "mūziķ", "albumu",
    "dziesm", "izstād", "muzej", "glezn", "balet", "kinofilm",
]
LEX_POLITICS = [
    "saeim", "ministr", "deputāt", "valdīb", "partij", "politiķ",
    "koalīcij", "opozīcij", "premjer", "vēlēšan", "frakcij", "likumprojekt",
    "pašvaldīb", "referendum",
]
# Particles / role words / refined stop set are the production lexicons —
# imported from src.matcher above so eval and matcher cannot drift. Only the
# UNREFINED base stop set stays local: it reproduces the pre-package matcher.
PARTICLES = _NAME_PARTICLES
_STOP_WORDS = {"un", "vai", "ar", "par", "no", "uz", "pie",
               "pēc", "kā", "bet", "gan", "arī"}


def default_cfg() -> dict:
    """boundary: False | 'all' (every form) | 'single' (one-word forms only).
    fn_refined adds the B2 fixes: multi-token first names, over-generated
    first-name declensions (Ata/Ulda/Raivja), Title-case requirement for a
    'foreign' token, sentence-boundary exemption, institutional exemption.
    handles=True adds registered @handles as confirmation + candidates."""
    return dict(boundary=False, fn_all=False, fn_particle=False,
                fn_refined=False, handles=False,
                domain=0, title=False, strip_negs=frozenset())


def occurrences(text: str, form: str, boundary: bool) -> list[int]:
    """All match offsets of form in text; boundary=True keeps only offsets
    whose neighbours are not letters (kills prefix/suffix substring bombs)."""
    out = []
    start = 0
    while True:
        idx = text.find(form, start)
        if idx == -1:
            break
        if boundary:
            before_ok = idx == 0 or not text[idx - 1].isalpha()
            end = idx + len(form)
            after_ok = end >= len(text) or not text[end].isalpha()
            if before_ok and after_ok:
                out.append(idx)
        else:
            out.append(idx)
        start = idx + 1
    return out


def _preceding_words(text: str, idx: int, window: int = 40) -> list[str]:
    return text[max(0, idx - window):idx].strip().split()


def _form_boundary(form: str, boundary) -> bool:
    """Whether the boundary check applies to this form under the cfg value."""
    if not boundary:
        return False
    if boundary == "single":
        return " " not in form
    return True  # 'all' / True


def match_variant(text: str, cfg: dict, forms_list, shared_set,
                  aux: dict | None = None) -> list[tuple[int, str]]:
    """Re-implementation of src.matcher.match_politicians with toggles.

    With default_cfg() this MUST be behaviourally identical to the real
    matcher (fidelity-checked in main()). Structure deliberately mirrors
    matcher.py so a reviewer can diff the two side by side.
    """
    boundary = cfg["boundary"]
    aux = aux or {}
    low = text.lower() if (cfg["handles"] or cfg["domain"]) else ""
    candidates: list[tuple[int, int, bool, list[str]]] = []

    dom_active = False
    if cfg["domain"]:
        dom_hits = sum(1 for s in LEX_DOMAIN if s in low)
        pol_hits = sum(1 for s in LEX_POLITICS if s in low)
        dom_active = dom_hits >= 2 and pol_hits == 0

    for pid, forms, pol_first_name, neg_patterns in forms_list:
        matched_forms = [
            f for f in forms
            if occurrences(text, f, _form_boundary(f, boundary))
        ]
        pol_aux = aux.get(pid, {})
        handle_conf = False
        if cfg["handles"] and pol_aux.get("handles"):
            handle_conf = any("@" + h in low for h in pol_aux["handles"])
            if handle_conf and not matched_forms:
                matched_forms = ["@" + next(iter(pol_aux["handles"]))]
        count = len(matched_forms)
        if count == 0:
            continue
        if pid not in cfg["strip_negs"]:
            if neg_patterns and any(p in text for p in neg_patterns):
                continue
        first_in_any = bool(pol_first_name) and any(pol_first_name in f for f in matched_forms)

        # domain guard (variant A)
        if dom_active:
            if cfg["domain"] >= 2 or not first_in_any:
                continue

        # common-word surname gate (verbatim from matcher.py)
        if (not handle_conf
                and all(" " not in f and f in M._COMMON_WORD_FORMS for f in matched_forms)):
            has_person_ctx = any(
                _surname_has_person_context(text, f) for f in matched_forms
            )
            if not has_person_ctx and pol_first_name:
                first_name_forms = (
                    {pol_first_name, *_latvian_surname_inflections(pol_first_name)}
                )
                for f in matched_forms:
                    for idx in occurrences(text, f, _form_boundary(f, boundary)):
                        before_words = _preceding_words(text, idx)
                        if before_words:
                            preceding = before_words[-1].rstrip(",;:.!?")
                            if preceding in first_name_forms:
                                has_person_ctx = True
                                break
                    if has_person_ctx:
                        break
            if not has_person_ctx:
                continue

        # foreign-first-name veto. Baseline: only when count==1 and the single
        # matched form lacks the first name. Variant fn_all: whenever NO
        # matched form carries the first name (any count).
        refined = cfg["fn_refined"]
        veto_exempt = handle_conf or (refined and pol_aux.get("institutional"))
        if cfg["fn_all"]:
            veto_scope = matched_forms if not (first_in_any or veto_exempt) else []
        else:
            only = matched_forms[0]
            veto_scope = (
                [only]
                if (count == 1 and not veto_exempt
                    and not (pol_first_name and pol_first_name in only))
                else []
            )
        if veto_scope:
            has_foreign = False
            has_correct = False
            if refined and pol_aux.get("tokens"):
                correct_forms = _first_token_decls(pol_aux["tokens"])
            else:
                correct_forms = (
                    {pol_first_name, *_latvian_surname_inflections(pol_first_name)}
                    if pol_first_name else set()
                )
            own_forms = set(matched_forms)

            # Refined mode uses the production closed-class stop set (incl.
            # sentence adverbs). The originally measured blanket
            # sentence-initial forgiveness was dropped — see module docstring.
            stops = _VETO_STOP_WORDS if refined else _STOP_WORDS

            def _classify(word: str, _correct=correct_forms, _own=own_forms,
                          refined=refined, _stops=stops) -> str:
                if word in _correct:
                    return "correct"
                if word in _own:
                    return "self"
                if (word and word[0].isupper() and len(word) > 2
                        and word.lower() not in _stops
                        and word.lower() not in _ROLE_WORDS
                        and not (refined and not any(c.islower() for c in word[1:]))):
                    return "foreign"
                return "other"

            for f in veto_scope:
                for idx in occurrences(text, f, _form_boundary(f, boundary)):
                    before_words = _preceding_words(text, idx)
                    if not before_words:
                        continue
                    raw = before_words[-1]
                    if refined and raw[-1] in _SENT_END:
                        # sentence boundary right before the surname — the
                        # capitalised token belongs to the previous sentence
                        continue
                    preceding = raw.rstrip(",;:.!?")
                    kind = _classify(preceding)
                    if (kind == "other" and cfg["fn_particle"]
                            and preceding.lower() in PARTICLES
                            and len(before_words) >= 2):
                        kind = _classify(before_words[-2].rstrip(",;:.!?"))
                    if kind == "correct":
                        has_correct = True
                    elif kind == "foreign":
                        has_foreign = True
            if has_foreign and not has_correct:
                continue

        has_unique = any(f not in shared_set for f in matched_forms)
        candidates.append((pid, count, has_unique, matched_forms))

    if not candidates:
        return []

    candidates.sort(key=lambda x: x[1], reverse=True)
    unique_candidates = [(pid, c) for pid, c, uniq, _ in candidates if uniq]
    shared_only = [(pid, c) for pid, c, uniq, _ in candidates if not uniq]

    kept_shared: list[tuple[int, int]] = []
    if shared_only:
        forms_by_pid = {p: (f, fn) for p, f, fn, _ in forms_list}
        for pid, c in shared_only:
            pol_forms, pol_first_name = forms_by_pid.get(pid, ([], ""))
            if not pol_first_name:
                continue
            first_name_forms = (
                {pol_first_name, *_latvian_surname_inflections(pol_first_name)}
            )
            has_proximity = False
            for f in pol_forms:
                for idx in occurrences(text, f, _form_boundary(f, boundary)):
                    before_words = _preceding_words(text, idx)
                    if before_words:
                        preceding = before_words[-1].rstrip(",;:.!?")
                        if preceding in first_name_forms:
                            has_proximity = True
                            break
                if has_proximity:
                    break
            if has_proximity:
                kept_shared.append((pid, c))

    all_candidates = unique_candidates + kept_shared
    result: list[tuple[int, str]] = []
    for i, (pid, _c) in enumerate(all_candidates):
        result.append((pid, "subject" if i == 0 else "mentioned"))
    return result


def evidence_profile(text: str, forms_list, pid: int) -> dict:
    """For a (text, pid) pair: which forms matched, and is any full-name?"""
    for p, forms, first, _neg in forms_list:
        if p != pid:
            continue
        matched = [f for f in forms if f in text]
        return {
            "matched": matched,
            "first_in_any": bool(first) and any(first in f for f in matched),
        }
    return {"matched": [], "first_in_any": False}


# ---------------------------------------------------------------------------

def load_datasets(db_path: str, quick: bool) -> dict:
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    docs: dict[int, dict] = {}

    def fetch_docs(ids: list[int]) -> None:
        for chunk_start in range(0, len(ids), 900):
            chunk = ids[chunk_start:chunk_start + 900]
            ph = ",".join("?" * len(chunk))
            for r in db.execute(
                f"""SELECT id, content, title, platform, source_url
                    FROM documents WHERE id IN ({ph})""",
                chunk,
            ):
                docs[r["id"]] = dict(r)

    fp_ids = [c["doc"] for c in FP_CASES]
    fetch_docs(fp_ids)

    handles: dict[int, set[str]] = {}
    for r in db.execute(
        "SELECT opponent_id, handle FROM social_accounts WHERE platform = 'twitter'"
    ):
        handles.setdefault(r["opponent_id"], set()).add(r["handle"].lower())

    gold_pairs_all = [
        (r["opponent_id"], r["document_id"])
        for r in db.execute(
            """SELECT DISTINCT opponent_id, document_id FROM claims
               WHERE document_id IS NOT NULL
                 AND claim_type IN ('position','commentary')"""
        )
    ]
    rng = random.Random(20260727)
    if quick:
        gold_pairs_all = rng.sample(gold_pairs_all, 600)
    fetch_docs(sorted({d for _, d in gold_pairs_all}))

    # Lane split. Twitter docs whose URL author IS the politician are linked
    # by the authorship path in _store_tweets, not by the text matcher —
    # matcher changes cannot lose them, so coverage is measured only on the
    # text-scan lane (web/vestnesis/relay tweets/x_mention).
    gold_pairs = []
    gold_author_lane = 0
    for pid, doc_id in gold_pairs_all:
        d = docs.get(doc_id)
        author = (
            extract_twitter_author_handle(d.get("source_url"))
            if d and d.get("platform") in ("twitter", "x_mention") else None
        )
        if author and author in handles.get(pid, set()):
            gold_author_lane += 1
        else:
            gold_pairs.append((pid, doc_id))

    silver_doc_ids = [
        r["document_id"]
        for r in db.execute("SELECT DISTINCT document_id FROM document_politicians")
    ]
    silver_sample = rng.sample(silver_doc_ids, 400 if quick else 3000)
    fetch_docs(silver_sample)
    silver_truth = {d: set() for d in silver_sample}
    for chunk_start in range(0, len(silver_sample), 900):
        chunk = silver_sample[chunk_start:chunk_start + 900]
        ph = ",".join("?" * len(chunk))
        for r in db.execute(
            f"""SELECT document_id, politician_id FROM document_politicians
                WHERE document_id IN ({ph})""",
            chunk,
        ):
            silver_truth[r["document_id"]].add(r["politician_id"])

    title_ids = [
        r["id"]
        for r in db.execute(
            """SELECT id FROM documents
               WHERE title IS NOT NULL AND title != ''
                 AND instr(content, title) = 0"""
        )
    ]
    if quick:
        title_ids = rng.sample(title_ids, 500)
    fetch_docs(title_ids)

    title_linked: dict[int, set] = {d: set() for d in title_ids}
    for chunk_start in range(0, len(title_ids), 900):
        chunk = title_ids[chunk_start:chunk_start + 900]
        ph = ",".join("?" * len(chunk))
        for r in db.execute(
            f"""SELECT document_id, politician_id FROM document_politicians
                WHERE document_id IN ({ph})""",
            chunk,
        ):
            title_linked[r["document_id"]].add(r["politician_id"])

    names = {r["id"]: r["name"] for r in db.execute("SELECT id, name FROM tracked_politicians")}
    db.close()
    return dict(docs=docs, gold_pairs=gold_pairs, gold_author_lane=gold_author_lane,
                silver_sample=silver_sample,
                silver_truth=silver_truth, title_ids=title_ids,
                title_linked=title_linked, names=names, handles=handles)


def run_variant(tag: str, cfg: dict, data: dict, forms_list, shared_set,
                aux: dict, base_results: dict | None) -> dict:
    """Run a cfg over FP + GOLD + SILVER doc sets. Returns per-doc pid sets."""
    docs = data["docs"]
    t0 = time.time()
    results: dict[int, set[int]] = {}
    doc_ids = set()
    doc_ids.update(c["doc"] for c in FP_CASES)
    doc_ids.update(d for _, d in data["gold_pairs"])
    doc_ids.update(data["silver_sample"])
    for doc_id in doc_ids:
        d = docs.get(doc_id)
        if not d or not d["content"]:
            results[doc_id] = set()
            continue
        text = d["content"]
        if cfg["title"] and d["title"] and d["title"] not in d["content"]:
            text = d["title"] + "\n\n" + d["content"]
        matches = match_variant(text, cfg, forms_list, shared_set, aux)
        if d["platform"] == "vestnesis" and matches:
            forms_by_pid = {p: f for p, f, _fn, _n in forms_list}
            matches = [
                (pid, role) for pid, role in matches
                if any(" " in f and f in text for f in forms_by_pid.get(pid, []))
            ]
        results[doc_id] = {pid for pid, _ in matches}

    fp_links = []
    for c in FP_CASES:
        if c["pid"] in results.get(c["doc"], set()):
            fp_links.append({**c})
    gold_lost = []
    gold_hit = 0
    for pid, doc_id in data["gold_pairs"]:
        if pid in results.get(doc_id, set()):
            gold_hit += 1
        elif base_results is None or pid in base_results.get(doc_id, set()):
            gold_lost.append((pid, doc_id))
    silver_removed = []
    silver_added = []
    if base_results is not None:
        for doc_id in data["silver_sample"]:
            for pid in base_results.get(doc_id, set()) - results.get(doc_id, set()):
                silver_removed.append((pid, doc_id))
            # Links the variant ADDS are as important as the ones it removes:
            # unreported additions are how the blanket sentence-initial rule
            # hid its reopening of the Abu-Meri class (see module docstring).
            for pid in results.get(doc_id, set()) - base_results.get(doc_id, set()):
                silver_added.append((pid, doc_id))
    return dict(tag=tag, cfg={k: (sorted(v) if isinstance(v, frozenset) else v)
                              for k, v in cfg.items()},
                results=results, fp_links=fp_links, gold_hit=gold_hit,
                gold_lost=gold_lost, silver_removed=silver_removed,
                silver_added=silver_added,
                secs=round(time.time() - t0, 1))


# Declared regression gates for the shipped B2D2H package (module docstring):
# fp_links ≤ 3 and gold_hit ≥ 1260. Enforced here so a matcher regression that
# reintroduces false links or silently drops gold coverage breaks the run.
REGRESSION_FP_LINKS_MAX = 3
REGRESSION_GOLD_HIT_MIN = 1260


def regression_gates_failed(b2d2h_run: dict) -> bool:
    """True when the B2D2H run breaks its declared regression gates."""
    return (
        len(b2d2h_run["fp_links"]) > REGRESSION_FP_LINKS_MAX
        or b2d2h_run["gold_hit"] < REGRESSION_GOLD_HIT_MIN
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="small samples, fast smoke")
    ap.add_argument("--out", default="eval_matcher_out.json")
    ap.add_argument("--db", default="data/atmina.db")
    args = ap.parse_args()

    _clear_politician_cache()
    forms_list = _load_politician_forms()
    shared_set = M._shared_surname_set

    aux_db = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    aux: dict[int, dict] = {}
    for pid, name, rel, xh in aux_db.execute(
        "SELECT id, name, relationship_type, x_handle FROM tracked_politicians"
    ):
        toks = (name or "").split()
        aux[pid] = {
            "tokens": toks[:-1] if len(toks) > 1 else [],
            "institutional": rel in ("journalist", "organization"),
            # legacy x_handle counts as a registered handle too — several
            # politicians have x_handle set but no social_accounts row
            "handles": {xh.lower().lstrip("@")} if xh else set(),
        }
    aux_db.close()

    import logging
    logging.getLogger("src.matcher").setLevel(logging.ERROR)

    data = load_datasets(args.db, args.quick)
    for pid, hs in data["handles"].items():
        if pid in aux:
            aux[pid]["handles"] |= hs
    print(f"datasets: fp={len(FP_CASES)} gold_text_lane={len(data['gold_pairs'])} "
          f"gold_author_lane={data['gold_author_lane']} "
          f"silver_docs={len(data['silver_sample'])} title_docs={len(data['title_ids'])} "
          f"docs_loaded={len(data['docs'])}")

    # ---- fidelity: engine(B2D2H) == real matcher ----------------------
    # The production matcher ships the B2D2H package since 2026-07-27, so the
    # gate pins THAT cfg to src.matcher. The default cfg re-implements the
    # pre-package matcher and stays as the delta baseline (not verifiable
    # against live code any more — frozen by this file's history).
    rng = random.Random(7)
    fid_ids = [c["doc"] for c in FP_CASES]
    gold_docs = sorted({d for _, d in data["gold_pairs"]})
    fid_ids += rng.sample(gold_docs, min(400, len(gold_docs)))
    fid_ids += rng.sample(data["silver_sample"], min(300, len(data["silver_sample"])))
    fid_ids += rng.sample(data["title_ids"], min(200, len(data["title_ids"])))
    mismatches = []
    cfg_prod = {**default_cfg(), "boundary": "single", "fn_all": True,
                "fn_particle": True, "fn_refined": True, "handles": True}
    for doc_id in fid_ids:
        d = data["docs"].get(doc_id)
        if not d or not d["content"]:
            continue
        a = match_politicians(d["content"])
        b = match_variant(d["content"], cfg_prod, forms_list, shared_set, aux)
        if a != b:
            mismatches.append({"doc": doc_id, "real": a, "engine": b})
    print(f"fidelity(B2D2H): {len(fid_ids)} docs checked, {len(mismatches)} mismatches")
    if mismatches:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"fidelity_mismatches": mismatches}, fh, ensure_ascii=False, indent=1)
        print("FIDELITY FAILED — engine diverges from src.matcher; report written, aborting.")
        return 2

    # ---- variant matrix ------------------------------------------------
    fp_pids = frozenset(c["pid"] for c in FP_CASES)
    matrix = [
        ("base", default_cfg()),
        ("D_all", {**default_cfg(), "boundary": "all"}),
        ("D2_single", {**default_cfg(), "boundary": "single"}),
        ("B_firstname", {**default_cfg(), "fn_all": True, "fn_particle": True}),
        ("B2_refined", {**default_cfg(), "fn_all": True, "fn_particle": True,
                        "fn_refined": True}),
        ("B2D2", {**default_cfg(), "boundary": "single", "fn_all": True,
                  "fn_particle": True, "fn_refined": True}),
        ("B2D2H", {**default_cfg(), "boundary": "single", "fn_all": True,
                   "fn_particle": True, "fn_refined": True, "handles": True}),
        ("A1_domain", {**default_cfg(), "domain": 1}),
        ("A2_domain", {**default_cfg(), "domain": 2}),
    ]
    runs = {}
    base_results = None
    for tag, cfg in matrix:
        r = run_variant(tag, cfg, data, forms_list, shared_set, aux, base_results)
        if tag == "base":
            base_results = r["results"]
        runs[tag] = r
        print(f"run {tag:12s} fp_links={len(r['fp_links']):2d} "
              f"gold={r['gold_hit']}/{len(data['gold_pairs'])} "
              f"gold_lost_vs_base={len(r['gold_lost'])} "
              f"silver_removed={len(r['silver_removed'])} "
              f"silver_added={len(r['silver_added'])} ({r['secs']}s)")

    # counterfactual: no negative_patterns for FP pids — would code alone stop them?
    cf_runs = {}
    for tag in ("base", "D_all", "D2_single", "B_firstname", "B2_refined", "B2D2H"):
        cfg = {**dict(runs[tag]["cfg"]), "strip_negs": fp_pids}
        cfg["title"] = False
        r_docs = {}
        for c in FP_CASES:
            d = data["docs"].get(c["doc"])
            if not d:
                continue
            mm = match_variant(d["content"], cfg, forms_list, shared_set, aux)
            r_docs[c["doc"]] = {pid for pid, _ in mm}
        linked = [c for c in FP_CASES if c["pid"] in r_docs.get(c["doc"], set())]
        cf_runs[tag] = linked
        print(f"counterfactual(no negpatterns) {tag:12s} fp_links={len(linked)}")

    # ---- evidence profile of gold pairs at base ------------------------
    bare_only = 0
    prof_missing = 0
    for pid, doc_id in data["gold_pairs"]:
        if base_results and pid in base_results.get(doc_id, set()):
            prof = evidence_profile(data["docs"][doc_id]["content"], forms_list, pid)
            if not prof["first_in_any"]:
                bare_only += 1
        else:
            prof_missing += 1

    # ---- title scan -----------------------------------------------------
    title_new: list[dict] = []
    for cfg_tag, cfg in (("T_base", {**default_cfg(), "title": True}),
                         ("T_B2D2H", {**default_cfg(), "title": True,
                                      "boundary": "single", "fn_all": True,
                                      "fn_particle": True, "fn_refined": True,
                                      "handles": True})):
        new_pairs = []
        for doc_id in data["title_ids"]:
            d = data["docs"][doc_id]
            if not d["content"] or not d["title"]:
                continue
            base_pids = {p for p, _ in match_variant(
                d["content"], {**cfg, "title": False}, forms_list, shared_set, aux)}
            t_pids = {p for p, _ in match_variant(
                d["title"] + "\n\n" + d["content"], cfg, forms_list, shared_set, aux)}
            for pid in t_pids - base_pids:
                prof = evidence_profile(d["title"], forms_list, pid)
                new_pairs.append({
                    "pid": pid, "name": data["names"].get(pid), "doc": doc_id,
                    "platform": d["platform"], "title": d["title"][:140],
                    "full_name_in_title": prof["first_in_any"],
                    "already_linked_other": bool(data["title_linked"].get(doc_id)),
                })
        title_new.append({"tag": cfg_tag, "n": len(new_pairs), "pairs": new_pairs})
        fn = sum(1 for p in new_pairs if p["full_name_in_title"])
        print(f"title-scan {cfg_tag}: +{len(new_pairs)} pairs "
              f"({fn} full-name-in-title, {len(new_pairs) - fn} bare)")

    # ---- report ---------------------------------------------------------
    def _pairs_named(pairs: list) -> list[dict]:
        out = []
        for pid, doc_id in pairs:
            d = data["docs"].get(doc_id, {})
            content = d.get("content") or ""
            prof = evidence_profile(content, forms_list, pid)
            handle_hit = any(
                "@" + h in content.lower()
                for h in data["handles"].get(pid, set())
            )
            snippet = ""
            if prof["matched"]:
                idx = content.find(prof["matched"][0])
                snippet = content[max(0, idx - 45):idx + len(prof["matched"][0]) + 45]
            out.append({"pid": pid, "name": data["names"].get(pid), "doc": doc_id,
                        "platform": d.get("platform"), "matched": prof["matched"],
                        "handle_in_text": handle_hit, "snippet": snippet})
        return out

    report = {
        "datasets": {
            "fp_cases": len(FP_CASES),
            "gold_pairs_text_lane": len(data["gold_pairs"]),
            "gold_pairs_author_lane": data["gold_author_lane"],
            "silver_docs": len(data["silver_sample"]),
            "title_docs": len(data["title_ids"]),
        },
        "fidelity_checked_docs": len(fid_ids),
        "gold_bare_only_share": {
            "bare_only": bare_only,
            "covered": len(data["gold_pairs"]) - prof_missing,
            "not_reproduced_by_base": prof_missing,
        },
        "variants": {
            tag: {
                "cfg": r["cfg"],
                "fp_links_residual": len(r["fp_links"]),
                "fp_links": [
                    {k: v for k, v in c.items() if k != "src"} for c in r["fp_links"]
                ],
                "gold_hit": r["gold_hit"],
                "gold_lost_vs_base": _pairs_named(r["gold_lost"]),
                "silver_removed_vs_base": _pairs_named(r["silver_removed"]),
                "silver_added_vs_base": _pairs_named(r["silver_added"]),
                "secs": r["secs"],
            }
            for tag, r in runs.items()
        },
        "counterfactual_no_negpatterns": {
            tag: [c["label"] for c in linked] for tag, linked in cf_runs.items()
        },
        "title_scan": title_new,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print("report ->", args.out)
    if regression_gates_failed(runs["B2D2H"]):
        r = runs["B2D2H"]
        print(
            f"REGRESSION GATES FAILED — B2D2H fp_links={len(r['fp_links'])} "
            f"(gate ≤ {REGRESSION_FP_LINKS_MAX}), "
            f"gold_hit={r['gold_hit']} (gate ≥ {REGRESSION_GOLD_HIT_MIN})."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
