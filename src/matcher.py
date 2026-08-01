"""Politician name matching extracted from src.ingest in Phase 1 of
refactor-plan-2026-04-29.md.

Public surface (consumed by .claude/agents/* and scripts/* via the
src.ingest re-export shim — do NOT remove without bumping every consumer):

    extract_twitter_author_handle(source_url) -> str | None
    match_politicians(text, veto_log=None)    -> list[(pid, role)]
    match_politician(text)                    -> int | None
    link_politicians_to_documents(days, rescan_all=False) -> {doc_id: [pids]}
    assign_unmatched_documents(days)          -> {doc_id: pid}

Internal helpers (re-exported only for tests / eval harness):

    _clear_politician_cache, _load_politician_forms, _latvian_surname_inflections,
    _surname_has_person_context, _match_politician_from_url,
    _occurrences, _first_token_decls

Module state (all module-level globals are caches; clear via
_clear_politician_cache for test hygiene):

    _politician_forms_cache, _politician_aux_cache, _shared_surname_set,
    _SURNAME_DISAMBIGUATION

Matching model since 2026-07-27 (B2+D2+H package,
docs/plans/2026-07-27-matcher-koliziju-plans.md; measured by
scripts/eval_matcher_collisions.py):

    D2 — a single-word form only counts at word boundaries (both neighbours
         non-letters). Kills prefix bombs ("Kolu"→Kolumbija, "Lāci"→Lācis)
         and the -is phantom accusative ("Valainis"⊃"Valaini") that inflated
         match counts past the veto. Multi-word forms stay plain substrings.
    B2 — the foreign-first-name veto fires whenever NO matched form carries
         the politician's first name (any count), with refinements: exempt
         set from ALL leading name tokens in any declension (over-generated),
         ALL-CAPS tokens are not name signals, closed-class STOP set for
         pronouns and sentence-opening adverbs, name particles (del/van/…)
         look one word further back, institutional voices and
         handle-confirmed docs are exempt.
    H  — registered @handles (social_accounts ∪ tracked_politicians.x_handle,
         lowercase) are match forms and veto confirmation of their own.

Behavioral baseline pinned by tests/test_matcher.py + tests/fixtures/
matcher_docs.json.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from collections import Counter

from src.db import get_db, lv_cutoff


def extract_twitter_author_handle(source_url: str | None) -> str | None:
    """Parse the author screen_name from an x.com or twitter.com URL.

    Returns the handle in lowercase, or None if the URL is missing,
    not a Twitter/X URL, or malformed. Handles both x.com and
    twitter.com hosts, trailing slashes, and ?query params.
    """
    if not source_url:
        return None
    for prefix in ("https://x.com/", "https://twitter.com/", "http://x.com/", "http://twitter.com/"):
        if source_url.startswith(prefix):
            remainder = source_url[len(prefix):]
            handle = remainder.split("/", 1)[0].split("?", 1)[0].strip()
            return handle.lower() if handle else None
    return None


# --- Politician matching state ---

_politician_forms_cache: list[tuple[int, list[str], str, list[str]]] | None = None
# pid → {"tokens": [leading name tokens], "institutional": bool,
#        "handles": set[str lowercase, no @]} — populated alongside
# _politician_forms_cache by _load_politician_forms(). Consumers treat a
# missing entry as all-defaults, so tests that monkeypatch
# _load_politician_forms degrade gracefully (fallback veto exempt set,
# no handles, non-institutional).
_politician_aux_cache: dict[int, dict] | None = None
_shared_surname_set: set[str] = set()


def _clear_politician_cache() -> None:
    """Testing hook — resets the cached name forms and disambiguation
    rules so tests can mutate tracked_politicians and see their changes
    reflected in match_politicians(). Do not call from production code."""
    global _politician_forms_cache, _politician_aux_cache, \
        _shared_surname_set, _SURNAME_DISAMBIGUATION
    _politician_forms_cache = None
    _politician_aux_cache = None
    _shared_surname_set = set()
    _SURNAME_DISAMBIGUATION = {}


# Single-word surname forms that are also common Latvian words or place names.
# When ONLY these forms match (no full-name form), the match is rejected to
# prevent false positives like "Krasta iela" → Agnese Krasta.
_COMMON_WORD_FORMS: set[str] = {
    # krasts = shore/coast; "Krasta iela" is a major Rīga street
    "Krasta",
    # līdaka = pike (freshwater fish)
    "Līdaka",
    # dzintars = amber
    "Dzintars", "Dzintara", "Dzintaram",
    # putra = porridge
    "Putra",
    # lāce = she-bear
    "Lāce",
    # melnis = black grouse (bird)
    "Melnis",
    # zīle = great tit (bird)
    "Zīle", "Zīles", "Zīlem",
    # daudzi/daudziem = adjective "many" inflections that collide with
    # auto-generated acc/dat of surname Daudze (5th decl. fem. -e → -i/-ei).
    # Sentence-start capitalisation makes these visually identical to the
    # name forms; require person context to bind the match.
    "Daudzi", "Daudzei",
    # priede = pine tree; "Priedes iela" street names, sentence-start
    # "Priedes aug…" (Inga Priede seeded 2026-06-12)
    "Priede", "Priedes", "Priedei", "Priedi",
}

# Auto-derived inflections that are NEVER added as forms, even with the
# person-context gate above. "Daudzi atzina, ka…" (= "Many acknowledged…")
# defeats the gate: a sentence-start "Daudzi" followed by a speaking verb is
# indistinguishable from "surname + verb" person context, yet as a bare
# surname it would be accusative — grammatically impossible as the subject.
# Doc 50893 FP, operator-approved fix 2026-06-11. Cost: bare-accusative
# mentions ("satiku Daudzi") no longer match without the full name — rare.
# Compared lowercase; applies only to AUTO-derived inflections, never to
# forms explicitly present in name_forms.
_INFLECTION_COMMON_WORD_BLOCKLIST: set[str] = {"daudzi"}

# Words near the surname that signal a person reference (not a common word usage).
# Before surname: role/title words
_PERSON_CONTEXT_BEFORE = {
    "ministre", "ministrs", "ministrei", "ministram", "ministra",
    "deputāte", "deputāts", "deputātei", "deputātam", "deputāta",
    "premjere", "premjers", "premjerei", "premjeram", "premjera",
    "politiķe", "politiķis",
    "priekšsēdētāja", "priekšsēdētājs",
    "sekretāre", "sekretārs",
    "komisijas", "frakcijas", "partijas",
    "kundze", "kungs",
    "kolēģe", "kolēģis",
    "valsts", "ārlietu", "aizsardzības", "finanšu", "iekšlietu",
    "ekonomikas", "izglītības", "kultūras", "labklājības",
    "tieslietu", "satiksmes", "veselības", "vides", "zemkopības",
}
# After surname: speaking/action verbs typical for political reporting
_PERSON_CONTEXT_AFTER = {
    "paziņoja", "norādīja", "uzsvēra", "sacīja", "teica",
    "informēja", "piebilda", "skaidroja", "atzīmēja", "paskaidroja",
    "kritizēja", "aicināja", "rosināja", "piedāvāja", "iesniedza",
    "atbildēja", "uzskata", "atzina", "iebilda", "pieprasīja",
    "brīdināja", "solīja", "apgalvoja", "pauda", "vērtēja",
    "komentēja", "mudināja", "balsoja", "ierosināja", "apliecināja",
}

# --- Foreign-first-name veto lexicons (shared with the eval harness — keep
# scripts/eval_matcher_collisions.py importing these, not copying them) ------

# A capitalised token preceding a bare surname is NOT a foreign first name
# when it is a role/title word…
_ROLE_WORDS = {
    "ministrs", "ministre", "prezidents", "prezidente",
    "premjers", "premjere", "premjerministrs",
    "premjerministre", "deputāts", "deputāte",
    "saeimas", "valdības", "partijas", "frakcijas",
    "priekšsēdētājs", "priekšsēdētāja", "kungs",
    "kundze", "politiķis", "politiķe", "līderis",
    "līdere", "kandidāts", "kandidāte",
}
# …or a closed-class word that only carries a capital because it starts the
# sentence: pronouns/determiners ("Tie Bražes apzīmējumi") and the frequent
# sentence-opening adverbs/conjuncts of LV news prose (". Vienlaikus Kulbergs
# sacīja", ". Savukārt Valainis norādīja"). A curated CLOSED-class list is
# deliberate — a blanket "any sentence-initial capital is orthography" rule
# was tried in the 2026-07-27 eval and reopens the "Linda Abu Meri" class
# (foreign FULL NAME opening a sentence reads as orthography too). A missing
# adverb here costs one doc shape's coverage; it can never add a false link.
# Open classes (place names "Rīgā …", month names) stay out on purpose.
_VETO_STOP_WORDS = {
    "un", "vai", "ar", "par", "no", "uz", "pie", "pēc", "kā", "bet",
    "gan", "arī",
    # prepositions (closed class; only tokens >2 chars ever reach the
    # capitalisation check, but the short ones are free to keep)
    "aiz", "ap", "apakš", "abpus", "augšpus", "ārpus", "bez", "caur",
    "dēļ", "gar", "iekš", "iekšpus", "kopš", "lejpus", "līdz", "otrpus",
    "pa", "pār", "pirms", "pret", "starp", "šaipus", "virs", "viņpus",
    "zem",
    # pronouns / determiners
    "tie", "tas", "tā", "šis", "šī", "šie", "šīs", "viņš", "viņa",
    "viņi", "viņas", "mēs", "jūs", "es", "tu", "kas", "kurš", "kura",
    # sentence adverbs / conjuncts / particles
    "savukārt", "vienlaikus", "tāpat", "turklāt", "tomēr", "taču",
    "tikmēr", "turpretī", "turpretim", "proti", "piemēram", "visbeidzot",
    "pirmkārt", "otrkārt", "treškārt", "ceturtkārt", "iepriekš",
    "šodien", "vakar", "aizvakar", "rīt", "parīt", "patlaban", "pašlaik",
    "pagaidām", "kopumā", "galvenokārt", "acīmredzot", "iespējams",
    "protams", "diemžēl", "visticamāk", "turpmāk", "papildus",
    "vispirms", "sākotnēji", "beidzot", "nesen", "nupat", "tostarp",
    "citstarp", "turpat", "tāpēc", "tādēļ", "tātad", "vēlāk", "agrāk",
    "drīz", "drīzumā", "tobrīd", "pretēji", "visupirms", "attiecīgi",
    "pēcāk", "vēl", "jau", "tikai", "pat", "tur", "te", "šeit",
    "tagad", "tad", "vien", "tieši", "gandrīz", "varbūt", "laikam",
    "drīzāk", "citādi",
}
# Foreign-name particles: when the word directly before the surname is one of
# these, the actual name signal is one word further back ("Isaks del Toro").
_NAME_PARTICLES = {"del", "de", "van", "fon", "da", "di", "der"}
# Sentence-final characters: a preceding token ending in one of these belongs
# to the previous sentence and is no first-name signal for our surname.
_SENT_END = ".!?:;»”\"'"


def _occurrences(text: str, form: str) -> list[int]:
    """All match offsets of form in text. Single-word forms only count at
    word boundaries — both neighbours must be non-letters — which kills the
    prefix/suffix substring bombs ("Kolu"→"Kolumbija", "Lāci"→"Lācis",
    "Valaini" nested in "Valainis"). Multi-word forms keep plain substring
    semantics: boundary-checking phrase forms was measured to lose real
    coverage (declined phrase tails, "Abu Meri"⊂"Abu Merim")."""
    boundary = " " not in form
    out: list[int] = []
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


def _surname_has_person_context(text: str, surname: str) -> bool:
    """Check if any occurrence of surname in text appears in a person-name context.

    Returns True if at least one occurrence is preceded by a role/title word
    or followed by a speaking verb — strong signals it refers to a person,
    not a common Latvian word (e.g. "ministre Lāce" vs "lāce mežā").
    """
    start = 0
    while True:
        idx = text.find(surname, start)
        if idx == -1:
            break
        # Check preceding word (within 60 chars)
        before = text[max(0, idx - 60):idx].strip()
        before_words = before.split()
        if before_words:
            preceding = before_words[-1].rstrip(",;:.!?").lower()
            if preceding in _PERSON_CONTEXT_BEFORE:
                return True
        # Check following word (within 60 chars)
        after = text[idx + len(surname):idx + len(surname) + 60].strip()
        after_words = after.split()
        if after_words:
            following = after_words[0].rstrip(",;:.!?").lower()
            if following in _PERSON_CONTEXT_AFTER:
                return True
        start = idx + 1
    return False


def _latvian_surname_inflections(surname: str) -> list[str]:
    """Generate Latvian declension forms for a surname (gen/dat/acc).

    Latvian news routinely declines politician surnames — "par Melnim" (dative),
    "Sprūda izteikumi" (genitive), "atbalsta Šleseru" (accusative). The matcher
    is substring-based, so each declined form must be present in name_forms
    for the matcher to find it. Empty name_forms or nominative-only entries
    (e.g. Melnis: ['Kaspars Melnis', 'Melnis']) cause silent matcher misses.

    This generator covers the common patterns (~85% of LV surnames):
    - 2nd decl. masc. -is (Melnis, Staķis): nom-is, gen palatalized -a,
      dat -im, acc -i
    - 1st decl. masc. -s/-š/-ņš (Sprūds, Šlesers, Zivtiņš): nom, gen -a,
      dat -am, acc -u
    - 4th decl. fem. -a (Siliņa, Lapsa): nom, gen -as, dat -ai, acc -u
    - 5th decl. fem. -e: nom, gen -es, dat -ei, acc -i

    Skips handles (starting with @) and short tokens. Edge cases (compound
    surnames like "Abu Meri", foreign names) are best handled by manual
    name_forms entries — this function is additive, never overwrites.

    Collision caution: a masculine -ņš/-iņš surname inflects its genitive to
    -ņa/-iņa, which is identical to the -a feminine nominative of the same
    surname (Kļaviņš → gen. "Kļaviņa" == Līga *Kļaviņa*). A male holder's
    auto-inflections can therefore hijack a female same-surname politician's
    vote attribution. This caused the 2026-05-31 Kļaviņš↔Kļaviņa vote
    reattribution (journalist id=191 → deputy id=104) and slipped the P3
    deputy↔deputy collision sweep because it was journalist↔deputy. Guard
    same-surname m/f pairs with negative_patterns.
    """
    if not surname or surname.startswith("@") or len(surname) < 3:
        return []

    forms: list[str] = []

    # 2nd declension masculine -is (e.g., Melnis, Staķis, Krusts ends in -ts)
    if surname.endswith("is"):
        stem = surname[:-2]
        last = stem[-1] if stem else ""
        # Palatalization in genitive only (not dative/accusative):
        # n→ņ, l→ļ, t→š, d→ž, s→š, z→ž, c→č
        palatal = {"n": "ņ", "l": "ļ", "t": "š", "d": "ž",
                   "s": "š", "z": "ž", "c": "č"}
        gen_stem = (stem[:-1] + palatal[last]) if last in palatal else stem
        forms.extend([gen_stem + "a", stem + "im", stem + "i"])
    # 1st declension masculine -ņš (Zivtiņš)
    elif surname.endswith("ņš"):
        stem = surname[:-2]
        forms.extend([stem + "ņa", stem + "ņam", stem + "ņu"])
    # 1st declension masculine -š or -s (Sprūds, Šlesers, Smiltēns)
    elif surname.endswith("š") or (surname.endswith("s") and not surname.endswith("us")):
        stem = surname[:-1]
        forms.extend([stem + "a", stem + "am", stem + "u"])
    # 4th declension feminine -a (Siliņa, Švinka, Lapsa)
    elif surname.endswith("a"):
        stem = surname[:-1]
        forms.extend([stem + "as", stem + "ai", stem + "u"])
    # 5th declension feminine -e
    elif surname.endswith("e"):
        stem = surname[:-1]
        forms.extend([stem + "es", stem + "ei", stem + "i"])

    return forms


def _first_token_decls(tokens: list[str]) -> set[str]:
    """Declensions of every leading name token, deliberately over-generated:
    both palatalized and plain genitives (Valža UN Valda, Aša UN Ata) plus
    the labial j-insertion (Raivis→Raivja). Over-generation is safe here —
    these forms only EXEMPT a candidate from the foreign-first-name veto,
    they never create a match on their own."""
    out: set[str] = set()
    for tok in tokens:
        out.add(tok)
        out.update(_latvian_surname_inflections(tok))
        if tok.endswith("is") and len(tok) > 3:
            stem = tok[:-2]
            out.add(stem + "a")
            out.add(stem + "ja")
    return out


def _load_politician_forms() -> list[tuple[int, list[str], str, list[str]]]:
    """Load politician name forms from DB. Cached. Populates _shared_surname_set
    and _politician_aux_cache (veto exempt tokens, institutional flag,
    registered handles for H matching).

    Returns list of (pid, forms, first_name, negative_patterns) tuples.
    `negative_patterns` — list of substrings that, when present in the text
    around a name match, cause the candidate to be rejected. Used for
    name-collision cases like pid=146 Andris Bērziņš (ZZS deputy) vs. the
    former president of the same name.
    """
    global _politician_forms_cache, _politician_aux_cache, _shared_surname_set
    if _politician_forms_cache is not None:
        return _politician_forms_cache
    db = get_db()
    # Defensive: some fixture/fork DBs may lack negative_patterns. Check
    # the column list and fall back to a NULL literal if missing, so this
    # code path still works on stale schemas.
    tp_cols = {r[1] for r in db.execute("PRAGMA table_info(tracked_politicians)").fetchall()}
    neg_col = "negative_patterns" if "negative_patterns" in tp_cols else "NULL AS negative_patterns"
    # relationship_type controls auto-derive: institutional voices
    # ('journalist', 'organization') have last-token = common noun and
    # must NOT auto-add bare-surname forms or surname inflections.
    rel_col = "relationship_type" if "relationship_type" in tp_cols else "NULL AS relationship_type"
    # x_handle feeds registered-handle matching (H); legacy column, may be
    # absent on old fork DBs.
    xh_col = "x_handle" if "x_handle" in tp_cols else "NULL AS x_handle"
    rows = db.execute(
        f"SELECT id, name, name_forms, {neg_col}, {rel_col}, {xh_col} FROM tracked_politicians"
    ).fetchall()
    # Registered Twitter handles: social_accounts is authoritative, x_handle
    # is the legacy column — several politicians have only the latter, so H
    # matches on the union (both lowercase, no leading @).
    handles_by_pid: dict[int, set[str]] = {}
    try:
        for sa in db.execute(
            "SELECT opponent_id, handle FROM social_accounts WHERE platform = 'twitter'"
        ).fetchall():
            if sa["handle"]:
                handles_by_pid.setdefault(sa["opponent_id"], set()).add(sa["handle"].lower())
    except sqlite3.OperationalError:
        pass  # fixture/fork DB without social_accounts — x_handle still applies
    db.close()
    surnames = Counter(r["name"].split()[-1] for r in rows if r["name"].split())
    _shared_surname_set = {s for s, c in surnames.items() if c > 1}
    # Also mark INFLECTIONS of shared bare surnames as shared. Without this,
    # the has_unique check accepts "Kļaviņai" (dat. of Kļaviņa) as a unique
    # form even though both Līga Kļaviņa (104) and Jeļena Kļaviņa (100)
    # auto-inflect their bare surnames to the same set. The result was that
    # a salary line "Jeļenai Kļaviņai" matched BOTH politicians instead of
    # one — same root cause as the Judins/Hermanis collisions.
    # _disambiguate_shared_surname now sees the full inflection family and
    # can pick the right person from first-name context in text.
    for shared in list(_shared_surname_set):
        for inflection in _latvian_surname_inflections(shared):
            _shared_surname_set.add(inflection)
    result = []
    aux: dict[int, dict] = {}
    for r in rows:
        forms = json.loads(r["name_forms"]) if r["name_forms"] else []
        neg_patterns_raw = r["negative_patterns"]
        try:
            neg_patterns = json.loads(neg_patterns_raw) if neg_patterns_raw else []
        except (ValueError, TypeError):
            neg_patterns = []
        if not isinstance(neg_patterns, list):
            neg_patterns = []
        parts = r["name"].split()
        # Institutional voices (relationship_type 'journalist' or 'organization')
        # have last-token = common noun ("ziņas", "žurnāls", "Panorāma") rather
        # than a valid bare surname. For these, we must NOT auto-derive bare
        # last token or generate Latvian declensions — both would produce
        # widespread FPs from common-word substring matches. Tighten name_forms
        # explicitly per institutional voice instead. Added 2026-05-14 after
        # tightening-attempt failed because auto-derive sabotaged the tighten.
        #
        # This guard is also load-bearing for a REAL politician: Kārlis Seržants
        # (id=192) is kept relationship_type='journalist' on purpose because his
        # surname is the common noun "seržants" — auto-inflecting it (Seržanta /
        # Seržantam / ...) would match every "sergeant" in any text. Promoting
        # him to a full 'tracked' politician therefore needs a matcher CODE
        # change (a per-politician no-auto-inflect flag), NOT just a
        # relationship_type UPDATE. Do not "fix" his row.
        is_institutional = (r["relationship_type"] in ("journalist", "organization"))
        if parts:
            # Derive bare-surname and full-name forms carefully. The old
            # logic unconditionally added parts[-1], which for multi-word
            # surnames like "Hosams Abu Meri" injected the bare word "Meri"
            # into the form list — that then substring-matched unrelated
            # text like "Linda Abu Meri" (the 2026-04-10 name-match false
            # positive). The rules below avoid that:
            #
            #   (a) If name_forms is empty, fall back to deriving both the
            #       full name and the last token. This mis-handles compound
            #       surnames but matches prior behaviour for the 10
            #       politicians who currently lack explicit forms.
            #       Institutional voices skip the bare-token add — keep
            #       only the full name as a literal phrase match.
            #   (b) If name_forms is populated, only ADD the last token as
            #       a bare-surname form when the DB already contains a form
            #       of the shape "<first_name> <last_token>", which
            #       confirms the last token is a valid standalone surname
            #       (e.g. "Selma Levrence" → add "Levrence") rather than
            #       the tail of a compound (e.g. "Hosams Abu Meri" →
            #       do NOT add "Meri"). Institutional voices skip this too.
            if not forms:
                if len(parts) >= 2 and not is_institutional:
                    forms = [r["name"], parts[-1]]
                else:
                    forms = [r["name"]]
            else:
                if len(parts) >= 2 and not is_institutional:
                    surname_candidate = parts[-1]
                    first_last = f"{parts[0]} {surname_candidate}"
                    if first_last in forms and surname_candidate not in forms:
                        forms = forms + [surname_candidate]
            # Auto-extend with Latvian declension forms for the bare surname.
            # Additive: never replaces manual entries; only adds missing inflections.
            # Skip if the politician's "surname" is actually an X handle (@xxx).
            # Skip for institutional voices (see comment above).
            if (len(parts) >= 2
                    and not parts[-1].startswith("@")
                    and not is_institutional):
                inflections = _latvian_surname_inflections(parts[-1])
                for f in inflections:
                    if f not in forms and f.lower() not in _INFLECTION_COMMON_WORD_BLOCKLIST:
                        forms = forms + [f]
        result.append((r["id"], forms, parts[0] if parts else "", neg_patterns))
        pid_handles = set(handles_by_pid.get(r["id"], set()))
        if r["x_handle"]:
            pid_handles.add(r["x_handle"].lower().lstrip("@"))
        aux[r["id"]] = {
            # ALL leading name tokens ("Arturs Krišjānis" for A. K. Kariņš),
            # not just parts[0] — the veto exempt set covers each of them.
            "tokens": parts[:-1] if len(parts) > 1 else [],
            "institutional": is_institutional,
            "handles": pid_handles,
        }
    _politician_forms_cache = result
    _politician_aux_cache = aux
    return result


# Disambiguation: frozenset(candidate pids) → {clues: [(text, pid)], default: pid}
_SURNAME_DISAMBIGUATION: dict[frozenset, dict] = {}

# Disambiguation priority: lower = preferred when two politicians share
# a surname and no context clue resolves it. 'tracked' is the unified
# value for active politicians (post 2026-04-11 relationship_type split
# retirement); the old opponent/coalition_partner/potential_ally values
# are kept for any legacy rows that may survive in forked dev DBs.
_ROLE_PRIORITY = {"tracked": 1, "opponent": 1, "coalition_partner": 1,
                  "potential_ally": 1, "neutral": 4, "influencer": 5,
                  "journalist": 6}


def _init_surname_disambiguation():
    """Build disambiguation rules from DB data. Called once."""
    global _SURNAME_DISAMBIGUATION
    if _SURNAME_DISAMBIGUATION:
        return
    db = get_db()
    rows = db.execute("SELECT id, name, party, role, relationship_type FROM tracked_politicians").fetchall()
    db.close()
    pid_map = {r["id"]: dict(r) for r in rows}
    surname_groups: dict[str, list[int]] = {}
    for r in rows:
        surname_groups.setdefault(r["name"].split()[-1], []).append(r["id"])
    for pids in surname_groups.values():
        if len(pids) < 2:
            continue
        clues = []
        for pid in pids:
            p = pid_map[pid]
            clues.append((p["name"].split()[0], pid))
            if p["party"]:
                clues.append((p["party"], pid))
            if p["role"]:
                clues.extend((w, pid) for w in p["role"].split() if len(w) > 3)
        default = sorted(pids, key=lambda p: _ROLE_PRIORITY.get(pid_map[p].get("relationship_type", ""), 9))[0]
        _SURNAME_DISAMBIGUATION[frozenset(pids)] = {"clues": clues, "default": default}


def _disambiguate_shared_surname(text: str, candidates: list[tuple[int, int, bool]]) -> int | None:
    """Try to resolve ambiguous shared-surname match using context clues.

    Checks for first names, party names, role keywords in the text.
    Falls back to the more publicly prominent candidate (by relationship_type).
    """
    _init_surname_disambiguation()

    cand_pids = frozenset(c[0] for c in candidates)
    rule = _SURNAME_DISAMBIGUATION.get(cand_pids)
    if not rule:
        return None

    # Check context clues in order
    for clue_text, pid in rule["clues"]:
        if clue_text in text:
            return pid

    # No context clue found — use default (most prominent)
    return rule["default"]


def _match_politician_from_url(url: str) -> int | None:
    """Try to match a politician from URL path segments (e.g. NRA viedokli author slugs).

    Handles URLs like /viedokli/alvis-hermanis/517638-plans.htm
    by converting 'alvis-hermanis' → 'Alvis Hermanis' and matching against name forms.
    """
    # NRA viedokli pattern: /viedokli/<author-slug>/
    m = re.search(r'/viedokli/([\w-]+)/\d+', url)
    if not m:
        return None
    slug = m.group(1)  # e.g. "alvis-hermanis"
    # Convert slug to name: "alvis-hermanis" → "Alvis Hermanis"
    name_from_url = " ".join(w.capitalize() for w in slug.split("-"))
    return match_politician(name_from_url)


def match_politicians(
    text: str, veto_log: list[dict] | None = None
) -> list[tuple[int, str]]:
    """Match text to politicians by name forms. Returns list of (politician_id, role).

    First (highest-count) match gets role='subject', additional matches get
    'mentioned'. If the *only* matching forms are shared surnames (e.g.
    "Hermanis" when both Jānis Hermanis and Alvis Hermanis are tracked), the
    match is considered ambiguous — those candidates are skipped with a warning.

    Matching applies the B2+D2+H package (see module docstring): single-word
    forms count only at word boundaries, a registered @handle in the text is
    a match form of its own, and a candidate whose matched forms all lack the
    first name is vetoed when a foreign first name precedes the surname and
    the politician's own never does.

    ``veto_log`` is a pure observability hook: pass a list and every
    candidate the foreign-first-name veto discards appends one entry per
    foreign occurrence — {"pid", "form", "preceding", "snippet"} — without
    changing the result. /audit-integrity's B2-veto journal reads it.
    """
    forms_list = _load_politician_forms()
    aux = _politician_aux_cache or {}
    low = text.lower()

    # Track whether each candidate matched on unique (non-shared) forms
    candidates: list[tuple[int, int, bool]] = []  # (pid, count, has_unique)

    for pid, forms, pol_first_name, neg_patterns in forms_list:
        matched_forms = [f for f in forms if _occurrences(text, f)]
        pol_aux = aux.get(pid, {})
        handles = pol_aux.get("handles") or set()
        # H: a registered @handle in the text both confirms the person
        # (veto/common-word exemption) and, when no name form is present at
        # all (handle-only tweets), becomes the match itself.
        handle_conf = any("@" + h in low for h in handles)
        if handle_conf and not matched_forms:
            matched_forms = ["@" + sorted(handles)[0]]
        count = len(matched_forms)
        if count == 0:
            continue
        # Reject if any negative pattern appears in text — used for
        # name-collision cases like pid=146 Andris Bērziņš (ZZS deputy)
        # vs. the former president of the same name. Negative patterns
        # are configured per politician in the DB.
        if neg_patterns and any(p in text for p in neg_patterns):
            continue
        first_in_any = bool(pol_first_name) and any(
            pol_first_name in f for f in matched_forms
        )
        # If only common-word surname forms matched (no full name),
        # check whether the surname appears in a person context
        # (e.g. "ministre Lāce" or "Lāce paziņoja" → person,
        #  "Krasta iela" or "lāce mežā" → common word).
        if (not handle_conf
                and all(" " not in f and f in _COMMON_WORD_FORMS for f in matched_forms)):
            has_person_ctx = any(
                _surname_has_person_context(text, f) for f in matched_forms
            )
            # Latvian-declined first name preceding the surname is also
            # strong person context: "Raivim Dzintaram (NA)" — the role
            # word set doesn't include declined first names, but the
            # candidate's own first-name forms are a definitive signal.
            if not has_person_ctx and pol_first_name:
                first_name_forms = (
                    {pol_first_name, *_latvian_surname_inflections(pol_first_name)}
                )
                for f in matched_forms:
                    for idx in _occurrences(text, f):
                        before_words = text[max(0, idx - 40):idx].strip().split()
                        if before_words:
                            preceding = before_words[-1].rstrip(",;:.!?")
                            if preceding in first_name_forms:
                                has_person_ctx = True
                                break
                    if has_person_ctx:
                        break
            if not has_person_ctx:
                continue
        # Foreign-first-name veto (B2). Fires whenever NO matched form
        # carries the politician's first name — a full-name form anywhere in
        # the text is unambiguous, everything else must survive the scan
        # below. Institutional voices (their "first name" is not a person
        # name) and handle-confirmed docs are exempt.
        #
        # Scan ALL occurrences of every matched form and track two signals:
        # a "correct" preceding first name (= any leading token of the
        # politician's name, in ANY declension, deliberately over-generated
        # by _first_token_decls) and a "foreign" one (= some other
        # capitalised word that looks like a person name). Reject only when
        # foreign is present AND no correct signal appeared anywhere —
        # dense multi-politician texts routinely have both ("Evika Siliņa
        # … Melni, Siliņa uzsvēra").
        veto_exempt = handle_conf or bool(pol_aux.get("institutional"))
        if not (first_in_any or veto_exempt):
            if pol_aux.get("tokens"):
                correct_forms = _first_token_decls(pol_aux["tokens"])
            else:
                # No aux (monkeypatched forms in tests / stale cache):
                # fall back to declensions of the first token only.
                correct_forms = (
                    {pol_first_name, *_latvian_surname_inflections(pol_first_name)}
                    if pol_first_name else set()
                )
            own_forms = set(matched_forms)

            def _classify(word: str, _correct=correct_forms, _own=own_forms) -> str:
                if word in _correct:
                    return "correct"
                if word in _own:
                    # Self-repetition across sentences ("Sprūds. Sprūds
                    # sacīja…") — same politician, not a different person.
                    return "self"
                if (word and word[0].isupper() and len(word) > 2
                        and word.lower() not in _VETO_STOP_WORDS
                        and word.lower() not in _ROLE_WORDS
                        # ALL-CAPS tokens ("ĪSUMĀ", "LETA") are headings or
                        # acronyms, never first names — require Title-case.
                        and any(c.islower() for c in word[1:])):
                    return "foreign"
                return "other"

            has_foreign = False
            has_correct = False
            foreign_hits: list[tuple[str, str, int]] = []
            for f in matched_forms:
                for idx in _occurrences(text, f):
                    before_words = text[max(0, idx - 40):idx].strip().split()
                    if not before_words:
                        continue
                    raw = before_words[-1]
                    if raw[-1] in _SENT_END:
                        # Sentence boundary right before the surname — the
                        # capitalised token belongs to the previous sentence.
                        continue
                    preceding = raw.rstrip(",;:.!?")
                    foreign_token = preceding
                    kind = _classify(preceding)
                    # Foreign-name particle: "Isaks del Toro" — the word
                    # before the particle carries the actual name signal.
                    if (kind == "other"
                            and preceding.lower() in _NAME_PARTICLES
                            and len(before_words) >= 2):
                        particle_head = before_words[-2].rstrip(",;:.!?")
                        kind = _classify(particle_head)
                        foreign_token = particle_head
                    if kind == "correct":
                        has_correct = True
                    elif kind == "foreign":
                        has_foreign = True
                        foreign_hits.append((f, foreign_token, idx))
            if has_foreign and not has_correct:
                if veto_log is not None:
                    for hit_form, hit_prec, hit_idx in foreign_hits:
                        veto_log.append({
                            "pid": pid,
                            "form": hit_form,
                            "preceding": hit_prec,
                            "snippet": text[max(0, hit_idx - 45):
                                            hit_idx + len(hit_form) + 45],
                        })
                continue  # skip — different person with same surname
        has_unique = any(f not in _shared_surname_set for f in matched_forms)
        candidates.append((pid, count, has_unique))

    if not candidates:
        return []

    # Sort by count descending
    candidates.sort(key=lambda x: x[1], reverse=True)

    # Separate candidates with unique forms from shared-surname-only candidates.
    # A "unique form" is any matched form that no other tracked politician
    # can produce — typically a full "<first> <last>" entry. Shared-only
    # candidates need additional disambiguation before they're trusted.
    unique_candidates = [(pid, count) for pid, count, has_unique in candidates if has_unique]
    shared_only_candidates = [(pid, count) for pid, count, has_unique in candidates if not has_unique]

    # Per-candidate first-name proximity filter for shared-surname-only
    # candidates. The bare surname "Kļaviņai" alone matches both Līga
    # Kļaviņa (104) and Jeļena Kļaviņa (100). To decide which one(s) the
    # text actually refers to, scan each occurrence's preceding word and
    # check whether it equals the candidate's first name in ANY Latvian
    # declension. A candidate is kept only if at least one surname
    # occurrence has its first name immediately preceding (handles
    # "Jeļenai Kļaviņai" → only Jeļena (100), "Andrejam Judinam" →
    # only Andrejs (68); rejects Līga/Igors from the same texts).
    #
    # Truly ambiguous shared surnames with NO first-name context anywhere
    # (e.g. "Hermanis paziņoja...") return [] rather than guessing a
    # default — false attribution is the most expensive failure mode here.
    kept_shared: list[tuple[int, int]] = []
    if shared_only_candidates:
        forms_by_pid = {p: (f, fn) for p, f, fn, _ in forms_list}
        for pid, count in shared_only_candidates:
            pol_forms, pol_first_name = forms_by_pid.get(pid, ([], ""))
            if not pol_first_name:
                continue
            first_name_forms = (
                {pol_first_name, *_latvian_surname_inflections(pol_first_name)}
            )
            has_proximity = False
            for f in pol_forms:
                for idx in _occurrences(text, f):
                    before_words = text[max(0, idx - 40):idx].strip().split()
                    if before_words:
                        preceding = before_words[-1].rstrip(",;:.!?")
                        if preceding in first_name_forms:
                            has_proximity = True
                            break
                if has_proximity:
                    break
            if has_proximity:
                kept_shared.append((pid, count))

    all_candidates = unique_candidates + kept_shared

    if all_candidates:
        result: list[tuple[int, str]] = []
        for i, (pid, _count) in enumerate(all_candidates):
            role = "subject" if i == 0 else "mentioned"
            result.append((pid, role))
        return result

    # No unique forms and no shared-surname candidate has first-name
    # proximity — text is truly ambiguous. Log and return empty; the
    # operator can review unmatched_documents and assign manually.
    logger = logging.getLogger(__name__)
    ambig_pids = [c[0] for c in candidates]
    if ambig_pids:
        logger.warning(
            "Ambiguous politician match on shared surname — candidates: %s. "
            "No first-name context found near any occurrence; skipping.",
            ambig_pids,
        )
    return []


def match_politician(text: str) -> int | None:
    """Legacy wrapper — returns single best match."""
    matches = match_politicians(text)
    return matches[0][0] if matches else None


def _filter_vestnesis_strict(
    matches: list[tuple[int, str]], text: str
) -> list[tuple[int, str]]:
    """For vestnesis-platform docs, keep only politicians whose FULL NAME
    (multi-word form) appears in the text.

    Vestnesis docs (court rulings, decrees, signatory lists, izsoles,
    promotions) frequently contain surname-only homonyms of tracked
    politicians — e.g. doc 34376 lists `LINDA LIEPIŅA, dzim. 1980. gada
    27. decembrī, izsludināta par mirušu` (different person from LPV
    deputy Linda Liepiņa), or doc 34347 lists `Ozols` among 14 promoted
    officers (different from journalist Otto Ozols).

    Surname-only matches in vestnesis are too weak to act on — require
    full first+last form. Added 2026-05-13 after a 3-politician
    false-link audit (Liepiņa, Ozols, V. Valainis).
    """
    forms_list = _load_politician_forms()
    forms_by_pid = {pid: forms for pid, forms, _, _ in forms_list}
    filtered: list[tuple[int, str]] = []
    for pid, role in matches:
        forms = forms_by_pid.get(pid, [])
        full_forms = [f for f in forms if " " in f]
        if any(f in text for f in full_forms):
            filtered.append((pid, role))
    return filtered


def link_politicians_to_documents(
    days: int = 1,
    rescan_all: bool = False,
    doc_ids: list[int] | None = None,
) -> dict[int, list[int]]:
    """Scan documents and link politicians via document_politicians junction.

    If rescan_all=True, scans ALL documents (not just unlinked ones).
    Returns dict of {doc_id: [politician_ids]} for newly linked docs.

    ``doc_ids`` scans exactly those documents and ignores both the
    ``scraped_at`` window and the unlinked-only filter. It exists for
    backfills that REWRITE the content of old documents (see
    ``scripts/backfill_retweet_fulltext.py``): the text changed, so the
    politician scan must run again, but the documents are months old and
    already carry junctions. The obvious alternative — bumping ``scraped_at``
    so the normal window picks them up — is wrong: ``routine._check_analysis``
    compares ``documents.scraped_at`` against ``analyses.created_at``, so
    touching it on thousands of historical rows would re-open their
    politicians as "pending" for the daily routine.

    An empty list means "no documents"; it never falls back to the window.
    Junction writes are ``INSERT OR IGNORE``, so re-scanning a linked document
    adds what is new and disturbs nothing that is already there.
    """
    db = get_db()
    cutoff = lv_cutoff(days)

    if doc_ids is not None:
        if not doc_ids:
            db.close()
            return {}
        placeholders = ",".join("?" * len(doc_ids))
        rows = db.execute(
            f"SELECT id, content FROM documents WHERE id IN ({placeholders})",
            tuple(doc_ids),
        ).fetchall()
    elif rescan_all:
        rows = db.execute(
            "SELECT id, content FROM documents WHERE scraped_at >= ?", (cutoff,)
        ).fetchall()
    else:
        rows = db.execute("""
            SELECT d.id, d.content FROM documents d
            LEFT JOIN document_politicians dp ON dp.document_id = d.id
            WHERE dp.document_id IS NULL AND d.scraped_at >= ?
        """, (cutoff,)).fetchall()

    # Build pid -> set of registered Twitter handles (lowercase).
    # Used to decide whether the URL author of a tweet matches a
    # candidate politician. Set-based lookup means a single politician
    # can have multiple handles (primary + official + historical).
    pid_to_handles: dict[int, set[str]] = {}
    relay_handles: set[str] = set()  # lowercase handles of relay-type accounts
    sa_rows = db.execute(
        "SELECT handle, opponent_id, feed_type FROM social_accounts WHERE platform = 'twitter'"
    ).fetchall()
    for sa in sa_rows:
        h = sa["handle"].lower()
        pid_to_handles.setdefault(sa["opponent_id"], set()).add(h)
        if (sa["feed_type"] or "first_party") == "relay":
            relay_handles.add(h)

    linked: dict[int, list[int]] = {}
    for r in rows:
        matches = match_politicians(r["content"])
        if matches:
            doc_url = db.execute(
                "SELECT source_url, platform FROM documents WHERE id = ?", (r["id"],)
            ).fetchone()
            platform = doc_url["platform"] if doc_url else None
            source_url = doc_url["source_url"] if doc_url else None

            # Vestnesis-platform strictness: require full first+last name in
            # text. Surname-only matches on vestnesis docs (court rulings,
            # decree signatory lists, promotion lists, izsoles) almost always
            # indicate homonyms of tracked politicians, not the politicians
            # themselves. Added 2026-05-13 (sk. _filter_vestnesis_strict).
            if platform == "vestnesis":
                matches = _filter_vestnesis_strict(matches, r["content"])
                if not matches:
                    continue

            # For Twitter docs, extract the URL author handle. We compare
            # against each candidate politician's registered handles — no
            # dependency on the author being tracked. This catches tweets
            # by untracked authors (@KasparsH, @deduktors, @3DCADLV) that
            # mention a tracked politician.
            author_handle = (
                extract_twitter_author_handle(source_url)
                if platform == "twitter"
                else None
            )

            for pid, role in matches:
                # x_mention docs always store matches as mention_target. Their
                # author relationship is captured via documents.opponent_id at
                # ingest time (see src/x_mentions.py).
                if platform == "x_mention" and role == "subject":
                    role = "mention_target"
                # Twitter docs: subject role is reserved for tweets where the
                # URL author IS this politician (any of their registered handles).
                # Otherwise downgrade to 'mentioned' — applies to ALL non-self
                # authors, including relay accounts (LTV Ziņas reporting on a
                # politician AND demoted commentators critiquing one). The
                # earlier exemption for relay handles was only correct for
                # institutional reporting; it mislabeled commentator-targeted
                # politicians as 'subject'. See CHANGELOG 2026-04-25 for the
                # commentator demotion that surfaced this bug.
                elif (
                    platform == "twitter"
                    and role == "subject"
                    and author_handle is not None
                    and author_handle not in pid_to_handles.get(pid, set())
                ):
                    role = "mentioned"
                db.execute(
                    """INSERT OR IGNORE INTO document_politicians
                       (document_id, politician_id, role) VALUES (?, ?, ?)""",
                    (r["id"], pid, role),
                )
            linked[r["id"]] = [pid for pid, _ in matches]

    db.commit()
    db.close()
    return linked


def assign_unmatched_documents(days: int = 1) -> dict[int, int]:
    """Legacy wrapper. Returns {doc_id: politician_id} for first match only."""
    result = link_politicians_to_documents(days=days)
    return {doc_id: pids[0] for doc_id, pids in result.items() if pids}
