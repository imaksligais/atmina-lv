"""Audit stored `claims.quote` values for text that cannot be a first-party quote.

WHY THIS EXISTS
The 2026-07-25 deep-check run had `@devils-advocate` kill all six contradiction
candidates, and at least four died not because the politician was consistent
but because OUR stored text did not match the source: a journalist's third-
person paraphrase and a newspaper headline had been stored in `quote`, and one
tweet's sarcasm had been read as endorsement. Those claims render on public
profile pages with confidence 0.85-0.9. See BACKLOG § Stance-fidelity defekti.

WHAT IT FLAGS (read-only; it never writes)
1. `paraphrase` — the quote OPENS with the politician's own name or surname in
   the third person ("Čudars uzdevis...", "Indriksone uzskata..."). A quote is
   the person speaking; text ABOUT them in third person is the reporter's
   summary. This class is close to always a real defect.
1b. `paraphrase_mid` — the surname appears LATER in the quote, not at the start
   ("Valsts prezidenta nominētais premjera amata kandidāts Andris Kulbergs…").
   Added 2026-08-09, and the reason matters more than the class: until then the
   rule was prefix-only, so `paraphrase: 0` was a fact about the rule's reach,
   not about the corpus — 13 rows of this shape sat above the 0.85 audit
   threshold while the tool reported a clean sweep. It is deliberately a
   SEPARATE, weaker class: a genuine first-person quote may legitimately
   contain the speaker's own surname, so triage row by row, never in bulk.

EVERY CLASS PRINTS ITS DENOMINATOR (since 2026-08-09). "0" alone cannot be told
apart from "the query returned nothing" — and adding a denominator to a rule
that cannot find anything would only have made a false all-clear more
convincing, which is why the counter was fixed in the same change. The
denominators track `--min-confidence`, because a number measured over a
different set than the finding is not a denominator.
2. `headline` — the quote matches the source document's title. This is a WEAK
   signal and mostly NOT a defect: Latvian news headlines very often are a
   verbatim quote ("Es neesmu un nebūšu politiķis!"). It is a defect only when
   the headline is the journalist's framing (e.g. claim #113, an NRA headline).
   Triage by hand; do not batch-fix.
3. `paywall` — the source document is a paywalled stub, so the body the
   extractor saw was a lede plus boilerplate. Not a defect by itself, but the
   natural first audit set, since a stance drawn from a lede cannot carry much.
4. `misattributed_title` — the document title attributes its content to a
   tracked politician who is NOT this claim's owner ("Rajevs: …" stored under
   Sprūds). Added 2026-07-25 after claim #280 showed the first three classes
   all miss the worst failure: a whole interview with person A written up as
   person B's positions. #280 slipped through because its `quote` was NULL, so
   no quote-shaped test could see it. Triage by hand — an article headlined
   with A can legitimately also quote B.
5. `not_subject` — a first-party `position` whose owner has no `subject`
   junction on its own source document. WEAK and noisy on its own (a politician
   can be `mentioned` on a document that still carries their words, and the
   matcher's role assignment is imperfect), but it is the only structural
   signal that survives when both quote and title are uninformative. Read it as
   a pile to sample, never as a defect list.
6. `verbatim` — the quote is NOT a literal substring of its own document
   (`quote not in content`, no `_normalise`). Added 2026-08-09 (BACKLOG §
   Citātu integritātes (e)): the normalising headline rule cannot see
   punctuation drift, so a quote whose only divergence is punctuation used to
   pass as a full match — 569 such rows measured 2026-08-08, 179 of them a
   terminal-punctuation swap the tool would never have reported. The class
   reports EVERY literal miss (today ~1.4k incl. English quotes, ellipses and
   re-scraped corpora — overlap with classes 2-4 is by design, never make it
   exclusive), with its own denominator (`verbatim_checkable` = rows whose
   document is alive with non-empty content); triage row by row, never bulk.

Usage:
    .venv/Scripts/python.exe scripts/audit_quote_fidelity.py [--db PATH] [--min-confidence 0.0]
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "atmina.db"


def _normalise(text: str) -> str:
    return re.sub(r"[^\w ]", "", (text or "").lower()).strip()


_TITLE_LEAD_RE = re.compile(
    r"^([A-ZĀČĒĢĪĶĻŅŠŪŽ][\w āčēģīķļņšūž.-]{0,40}?)\s*:"
)


def _attribution_classes(db: sqlite3.Connection, min_confidence: float) -> dict[str, list[dict]]:
    """Misattribution signals that do NOT depend on the quote field.

    The first three classes all read `claims.quote`, so a claim with no quote is
    invisible to them no matter how wrongly it is attributed. These two read the
    document instead.
    """
    surname: dict[int, str] = {}
    for r in db.execute("SELECT id, name FROM tracked_politicians"):
        parts = (r["name"] or "").split()
        if parts:
            surname[r["id"]] = parts[-1]

    mis: list[dict] = []
    for r in db.execute(
        """SELECT c.id, c.confidence, c.opponent_id, c.source_url, tp.name, d.title
           FROM claims c
           JOIN tracked_politicians tp ON tp.id = c.opponent_id
           JOIN documents d ON d.id = c.document_id
           WHERE c.claim_type = 'position'
             AND d.title IS NOT NULL AND TRIM(d.title) != ''
             AND c.confidence >= ?""",
        (min_confidence,),
    ):
        m = _TITLE_LEAD_RE.match((r["title"] or "").strip())
        if not m:
            continue
        lead = m.group(1)
        own = surname.get(r["opponent_id"], "")
        if own and own in lead:
            continue  # headline attributes to the claim's own owner — fine
        others = [pid for pid, s in surname.items()
                  if s and s in lead and pid != r["opponent_id"]]
        if not others:
            continue
        mis.append({
            "id": r["id"], "name": r["name"], "confidence": r["confidence"],
            "quote": f"virsraksts attiecina: {surname[others[0]]} — {(r['title'] or '')[:60]}",
            "source_url": r["source_url"],
        })

    not_subj = [
        {"id": r["id"], "name": r["name"], "confidence": r["confidence"],
         "quote": (r["stance"] or "")[:62], "source_url": r["source_url"]}
        for r in db.execute(
            """SELECT c.id, c.confidence, c.stance, c.source_url, tp.name
               FROM claims c
               JOIN tracked_politicians tp ON tp.id = c.opponent_id
               WHERE c.claim_type = 'position' AND c.document_id IS NOT NULL
                 AND c.confidence >= ?
                 AND NOT EXISTS (
                     SELECT 1 FROM document_politicians dp
                     WHERE dp.document_id = c.document_id
                       AND dp.politician_id = c.opponent_id
                       AND dp.role = 'subject')""",
            (min_confidence,),
        )
    ]
    return {"misattributed_title": mis, "not_subject": not_subj}


def audit(db_path: str, min_confidence: float = 0.0) -> dict[str, list[dict]]:
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """SELECT c.id, c.confidence, c.salience, c.quote, c.stance, c.source_url,
                  tp.name, d.is_paywall, d.title, d.content
           FROM claims c
           JOIN tracked_politicians tp ON tp.id = c.opponent_id
           LEFT JOIN documents d ON d.id = c.document_id
           WHERE c.claim_type = 'position'
             AND c.quote IS NOT NULL AND TRIM(c.quote) != ''
             AND c.confidence >= ?""",
        (min_confidence,),
    ).fetchall()
    # SAUCĒJI — skaitīti pret TO PAŠU filtru, ko lieto klases (2026-08-09).
    # Bez tiem „paraphrase: 0" nav atšķirams no „vaicājums neko neatdeva".
    # `no_quote` ir klases aklā zona, ne defekts: `@claim-extractor` §8 TIEŠI
    # atļauj `quote=null`, tāpēc regresija tajā virzienā pievieno rindas, kuras
    # trīs no piecām klasēm neredz vispār.
    # `verbatim_checkable` (2026-08-09, klase 6): rēķina NO rows objekta — tas
    # pats filtrs, ko cilpa tiešām lieto; atsevišķs SQL varētu aizdriftēt.
    # verbatim_checkable <= quoted: bāreņa claim (documents rindas nav) ir
    # 'quoted', bet nav burtiski pārbaudāms — SEGUMS rādā abus skaitļus.
    denom = {
        "quoted": len(rows),
        "verbatim_checkable": sum(
            1 for r in rows if (r["content"] or "").strip()
        ),
        "no_quote": db.execute(
            """SELECT COUNT(*) FROM claims c
               WHERE c.claim_type='position' AND c.confidence >= ?
                 AND (c.quote IS NULL OR TRIM(c.quote) = '')""",
            (min_confidence,),
        ).fetchone()[0],
        "titled": db.execute(
            """SELECT COUNT(*) FROM claims c JOIN documents d ON d.id = c.document_id
               WHERE c.claim_type='position' AND c.confidence >= ?
                 AND d.title IS NOT NULL AND TRIM(d.title) != ''""",
            (min_confidence,),
        ).fetchone()[0],
    }
    attribution = _attribution_classes(db, min_confidence)
    db.close()

    found: dict[str, list[dict]] = {
        "paraphrase": [], "paraphrase_mid": [], "headline": [], "paywall": [],
        "verbatim": [],
    }
    for r in rows:
        quote = (r["quote"] or "").strip()
        name = r["name"] or ""
        surname = name.split()[-1] if name else ""
        entry = {
            "id": r["id"], "name": name, "confidence": r["confidence"],
            "quote": quote, "source_url": r["source_url"],
        }

        content = r["content"] or ""
        if content.strip() and quote not in content:
            # Klase 6 (2026-08-09): burtiskā apakšvirkne BEZ _normalise —
            # pieturzīmju atkāpe, ko normalizējošie testi nekad neredz.
            # Bez garuma sliekšņa: īss citāts ir tikpat pārbaudāms.
            found["verbatim"].append(entry)

        if name and (quote.startswith(name) or (surname and quote.startswith(surname + " "))):
            found["paraphrase"].append(entry)
        elif surname and len(surname) >= 5 and re.search(r"\b" + re.escape(surname), quote):
            # Skaitītāja labojums (2026-08-09). Līdz tam parafrāzes likums bija
            # TIKAI prefikss, tāpēc „paraphrase: 0" bija fakts par likuma
            # tvērumu, ne par korpusu: atstāsti, kuros uzvārds stāv teikuma
            # vidū („Valsts prezidenta nominētais premjera amata kandidāts
            # Andris Kulbergs…"), palika neredzami. Atsevišķa klase ar savu
            # saucēju, jo tā ir VĀJĀKA par prefiksa formu — īsts pirmās
            # personas citāts drīkst saturēt paša uzvārdu, tāpēc rindu-pa-rindai
            # triāža, nekad batch.
            found["paraphrase_mid"].append(entry)

        title = (r["title"] or "").strip()
        if title and len(quote) > 15:
            q, t = _normalise(quote), _normalise(title)
            if q and (q in t or t in q):
                found["headline"].append(entry)

        if r["is_paywall"]:
            found["paywall"].append(entry)

    found.update(attribution)
    return found, denom


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--min-confidence", type=float, default=0.0)
    args = ap.parse_args()

    found, denom = audit(args.db, args.min_confidence)

    print("Quote-fidelity audit (read-only)\n")
    print(f"SEGUMS (conf>={args.min_confidence}): {denom['quoted']} pozīcijas ar citātu, "
          f"{denom['verbatim_checkable']} burtiski pārbaudāmas (dzīvs dokuments), "
          f"{denom['no_quote']} BEZ citāta (citāta klasēm neredzamas), "
          f"{denom['titled']} ar netukšu virsrakstu.")
    if denom["no_quote"]:
        print("   NB: `quote=null` ir atļauts (claim-extractor §8), tāpēc regresija "
              "tajā virzienā dod 0 gan skaitītājā, gan bez šīs rindas — arī saucējā.")
    for k, v in denom.items():
        if v <= 1:
            print(f"   UZMANĪBU: saucējs `{k}` ir {v} — tie nav tīri dati, tie ir salauzti vārti.")
    print()

    labels = {
        "paraphrase": "3. personas parafrāze citāta SĀKUMĀ — gandrīz vienmēr īsts defekts",
        "paraphrase_mid": "uzvārds citāta VIDŪ — vājāks signāls, rindu-pa-rindai triāža (2026-08-09)",
        "headline": "citāts sakrīt ar virsrakstu — VĀJŠ signāls, jātriažē ar roku",
        "paywall": "avots ir paywall stubs — audita kopums, ne defekts pats par sevi",
        "misattributed_title": "virsraksts attiecina CITAM politiķim — neatkarīgs no citāta, jātriažē ar roku",
        "not_subject": "position bez 'subject' saites uz savu doku — VĀJŠ, paraugu kopums, ne defektu saraksts",
        "verbatim": "citāts NAV burtiska apakšvirkne dokumentā — (e) klase, rindu-pa-rindai triāža (2026-08-09)",
    }
    # Katrai klasei TĀS PATS saucējs, pret kuru tā tiešām skatījās.
    denom_for = {
        "paraphrase": denom["quoted"], "paraphrase_mid": denom["quoted"],
        "headline": denom["quoted"], "paywall": denom["quoted"],
        "misattributed_title": denom["titled"],
        "verbatim": denom["verbatim_checkable"],
    }
    for key, entries in found.items():
        strong = sum(1 for e in entries if e["confidence"] >= 0.85)
        d = denom_for.get(key)
        n = f"{len(entries)}/{d}" if d is not None else f"{len(entries)}"
        print(f"== {key}: {n} (conf>=0.85: {strong}) — {labels.get(key, key)}")
        for e in sorted(entries, key=lambda e: -e["confidence"])[:40]:
            print(f"   #{e['id']:<8} conf={e['confidence']:<5} {e['name'][:22]:<23} {e['quote'][:62]}")
        print()

    print("Nekas nav mainīts. Katrs labojums prasa pāra rollback + operatora apstiprinājumu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
