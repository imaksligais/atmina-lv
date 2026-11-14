"""Pretrunas faktu pārbaude pret avotiem — pirms glabāšanas un pirms publicēšanas.

Kāpēc: 2026-11-13 pārskatā 12 no 37 publicētajām pretrunām saturēja kļūdainu
faktu («visa frakcija atturējās», neburtisks citāts, cits balsojuma rezultāts),
lai gan visas bija izgājušas `@devils-advocate`. Kopsavilkumu neviens nebija
salicis blakus balsojumu tabulai un avota tekstam.

Divas daļas:
- `fact_sheet()` — ko par abām pusēm saka DB: balsojums, paša balss, frakcijas
  sadalījums TAJĀ balsojumā, visa `document_nr` ķēde (T14), avota teksts.
- `check_text()` — kopsavilkuma apgalvojumi pret šo lapu. `KĻŪDA` aptur;
  `PĀRBAUDI` nozīmē, ka mašīna nevar izšķirt un lasītājam jāsalīdzina pašam.

Tikai lasa. Mehāniskā pārbaude noķer daļu kļūdu, ne visas: faktu lapa ir tā,
ko lasītājs (`@devils-advocate`, orķestrators) saliek blakus tekstam.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Any

from src.party_contradictions import is_procedural
from src.saeima.petitions import is_petition_decision_vote
from src.support import norm, unverbatim_quotes

ERROR = "KĻŪDA"
CHECK = "PĀRBAUDI"

_CAST = ("Par", "Pret", "Atturas")
_BALLOT_WORDS = ("Par", "Pret", "Atturas", "Nebalsoja")
_MONTHS = {
    "janvār": 1, "februār": 2, "mart": 3, "aprīl": 4, "maij": 5, "jūnij": 6,
    "jūlij": 7, "august": 8, "septembr": 9, "oktobr": 10, "novembr": 11, "decembr": 12,
}
_TALLY = re.compile(r"(?<![\d:.])(\d{1,3}):(\d{1,3})(?::(\d{1,3}))?(?![\d:])")
_DATE_WORDS = re.compile(
    r"(?:(\d{4})\.\s*gada\s+)?(\d{1,2})\.\s*(" + "|".join(_MONTHS) + r")\w*", re.IGNORECASE
)
_DATE_NUM = re.compile(r"(?<![\d.])(\d{1,2})\.(\d{1,2})\.(?:(\d{4}))?")
_UNANIMOUS = re.compile(
    # «visi klātesošie deputāti» ir visa Saeima, ne frakcija — to te neķer (#56).
    r"vis[ai]s?\s+(?:\S+\s+){0,3}?(?:frakcij|koalīcij)\w*|vienot[ia]\b|vienbalsīg\w*|vienprātīg\w*",
    re.IGNORECASE,
)
_SAID_AGAINST = re.compile(r"balsoj\w*\s+(?:«)?pret\b", re.IGNORECASE)
_SAID_ABSTAIN = re.compile(r"attur", re.IGNORECASE)
# Citāts sola burtiskumu neatkarīgi no pēdiņu veida: "…", „…“ un “…” lasa kā «…».
_OTHER_QUOTES = re.compile(r"[\"„“]([^\"„“”«»\n]{3,}?)[\"“”]")


@dataclass(frozen=True)
class Problem:
    level: str  # ERROR vai CHECK
    kind: str
    message: str

    def __str__(self) -> str:
        return f"{self.level} [{self.kind}] {self.message}"


def _distribution(db: sqlite3.Connection, vote_id: int, faction: str | None, party: str | None) -> dict[str, Any]:
    """Frakcijas sadalījums VIENĀ balsojumā; partija tikai tad, ja frakciju nav nevienam."""
    total, nulls = db.execute(
        "SELECT COUNT(*), SUM(faction IS NULL) FROM saeima_individual_votes WHERE vote_id = ?", (vote_id,)
    ).fetchone()
    if total and total == nulls:
        # 15. Saeimas pagaidu izņēmums (operators 2026-11-09): frakciju nav nevienam.
        rows = db.execute(
            """SELECT siv.vote, COUNT(*) FROM saeima_individual_votes siv
               JOIN tracked_politicians tp ON tp.id = siv.politician_id
               WHERE siv.vote_id = ? AND tp.party = ? GROUP BY siv.vote""",
            (vote_id, party),
        ).fetchall()
        basis = f"partija «{party}» (frakcijas balsojumā nav reģistrētas)" if party else "nav nosakāms (partija nav zināma)"
        return {"basis": basis, "counts": {r[0]: r[1] for r in rows} if party else {}}
    if faction is None:
        return {"basis": "deputāts šajā balsojumā ārpus frakcijām", "counts": {}}
    rows = db.execute(
        "SELECT vote, COUNT(*) FROM saeima_individual_votes WHERE vote_id = ? AND faction = ? GROUP BY vote",
        (vote_id, faction),
    ).fetchall()
    return {"basis": f"frakcija {faction}", "counts": {r[0]: r[1] for r in rows}}


def _vote_facts(db: sqlite3.Connection, vote: sqlite3.Row, pid: int, party: str | None) -> dict[str, Any]:
    own = db.execute(
        "SELECT vote, faction FROM saeima_individual_votes WHERE vote_id = ? AND politician_id = ?",
        (vote["id"], pid),
    ).fetchone()
    return {
        "id": vote["id"],
        "date": vote["vote_date"],
        "time": vote["vote_time"],
        "motif": vote["motif"] or "",
        "summary": vote["summary"] or "",
        "document_nr": vote["document_nr"],
        "result": vote["result"],
        "tally": (vote["total_par"], vote["total_pret"], vote["total_atturas"]),
        "own": own["vote"] if own else None,
        "faction": _distribution(db, vote["id"], own["faction"] if own else None, party),
        "procedural": is_procedural(vote["motif"]),
        "petition": is_petition_decision_vote(vote["motif"]),
    }


def _side(db: sqlite3.Connection, claim_id: int, pid: int, party: str | None) -> dict[str, Any]:
    c = db.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
    if c is None:
        return {"claim_id": claim_id, "missing": True}
    side: dict[str, Any] = {
        "claim_id": claim_id,
        "claim_type": c["claim_type"],
        "stated_at": c["stated_at"],
        "stance": c["stance"] or "",
        "quote": c["quote"] or "",
        "source_url": c["source_url"],
        "review_status": c["review_status"],
        "third_party": c["speaker_id"] is not None and c["speaker_id"] != c["opponent_id"],
        "wrong_politician": c["opponent_id"] != pid,
        "doc_text": "",
        "doc_date": None,
        "vote": None,
        "chain": [],
    }
    if c["document_id"]:
        d = db.execute("SELECT title, content, published_at FROM documents WHERE id = ?", (c["document_id"],)).fetchone()
        if d:
            side["doc_text"] = f"{d['title'] or ''}\n{d['content'] or ''}"
            side["doc_date"] = d["published_at"]
    # Saeimas tabulas veido `init_saeima_tables`, ne `init_db`; DB bez tām = balsojumu nav.
    has_votes = db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'saeima_votes'").fetchone()
    v = db.execute("SELECT * FROM saeima_votes WHERE url = ?", (c["source_url"],)).fetchone() if has_votes else None
    if v:
        side["vote"] = _vote_facts(db, v, pid, party)
        if v["document_nr"]:
            chain = db.execute(
                "SELECT * FROM saeima_votes WHERE document_nr = ? ORDER BY vote_date, vote_time", (v["document_nr"],)
            ).fetchall()
            side["chain"] = [_vote_facts(db, cv, pid, party) for cv in chain]
    return side


def fact_sheet(db: sqlite3.Connection, opponent_id: int, claim_old_id: int, claim_new_id: int) -> dict[str, Any]:
    """Ko DB zina par pretrunas abām pusēm. `db` vajag `row_factory = sqlite3.Row`."""
    p = db.execute("SELECT name, party FROM tracked_politicians WHERE id = ?", (opponent_id,)).fetchone()
    party = p["party"] if p else None
    return {
        "politician_id": opponent_id,
        "politician": p["name"] if p else None,
        "party": party,
        "sides": [_side(db, cid, opponent_id, party) for cid in (claim_old_id, claim_new_id)],
    }


def find_quote_elsewhere(db: sqlite3.Connection, pid: int, fragment: str) -> dict[str, Any] | None:
    """Citāts, kura nav pretrunas abos avotos: vai tas ir citā šī politiķa dokumentā?"""
    words = [w for w in fragment.split() if re.fullmatch(r"[\w-]+[.,]?", w)]
    probe = " ".join(words[:3]).rstrip(".,") if len(words) >= 3 else (max(words, key=len).rstrip(".,") if words else "")
    if len(probe) < 6:
        return None
    rows = db.execute(
        """SELECT d.id, d.published_at, d.source_url, d.title, d.content FROM documents d
           JOIN document_politicians dp ON dp.document_id = d.id
           WHERE dp.politician_id = ? AND d.content LIKE ? LIMIT 200""",
        (pid, f"%{probe}%"),
    ).fetchall()
    want = norm(fragment).rstrip(".,!?…").casefold()
    for r in rows:
        if want in norm(f"{r['title'] or ''}\n{r['content'] or ''}").casefold():
            return {"where": f"dokumentā {r['id']} ({(r['published_at'] or '')[:10]}, {r['source_url']})"}
    for r in db.execute(  # likumprojekta nosaukums pēdiņās: cita balsojuma motīvs
        "SELECT id, vote_date, motif FROM saeima_votes WHERE motif LIKE ? LIMIT 50", (f"%{probe}%",)
    ):
        if want in norm(r["motif"] or "").casefold():
            return {"where": f"balsojuma {r['id']} ({r['vote_date']}) nosaukumā"}
    return None


def _votes(sheet: dict[str, Any]) -> list[dict[str, Any]]:
    """Visi balsojumi, uz kuriem kopsavilkums drīkst atsaukties: abu pušu ķēdes."""
    seen: dict[int, dict[str, Any]] = {}
    for s in sheet["sides"]:
        for v in ([s["vote"]] if s.get("vote") else []) + s.get("chain", []):
            seen[v["id"]] = v
    return list(seen.values())


def _known_dates(sheet: dict[str, Any]) -> set[tuple[int, int]]:
    out: set[tuple[int, int]] = set()
    raw = [v["date"] for v in _votes(sheet)]
    for s in sheet["sides"]:
        raw += [s.get("stated_at"), s.get("doc_date")]
    for r in raw:
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", r or "")
        if m:
            out.add((int(m.group(3)), int(m.group(2))))
    return out


def _unanimous(counts: dict[str, int]) -> bool:
    cast = {k: n for k, n in counts.items() if k in _CAST and n}
    return len(cast) == 1


def _fmt_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{k} {n}" for k, n in sorted(counts.items())) or "nav balsu"


def check_text(
    sheet: dict[str, Any],
    summary: str,
    headline: str | None = None,
    extra_sources: list[dict[str, str]] | None = None,
    db: sqlite3.Connection | None = None,
) -> list[Problem]:
    """Kopsavilkuma apgalvojumi pret faktu lapu. Tukšs saraksts = mašīna neko neatrada.

    Balsis, skaitļus un datumus pārbauda tikai galvenajā daļā un virsrakstā:
    `[Konteksts: …]` likumīgi apraksta citu cilvēku balsis un citas dienas.
    Ar `db` citātu, kura nav abos avotos, meklē pārējos politiķa dokumentos.
    """
    out: list[Problem] = []
    # Tā pati iekavu robeža kā renderā (`_split_summary`); renderu te neimportē —
    # šo moduli sauc `src.db.store_contradiction`.
    main = re.sub(r"\s*\[[^\]]+\]", "", summary or "").strip()
    text = f"{main} {headline or ''}"
    sides = sheet["sides"]
    votes = _votes(sheet)
    linked = [s["vote"] for s in sides if s.get("vote")]

    for s in sides:
        if s.get("missing"):
            out.append(Problem(ERROR, "claim", f"pozīcija {s['claim_id']} neeksistē"))
            continue
        if s["wrong_politician"]:
            out.append(Problem(ERROR, "claim", f"pozīcija {s['claim_id']} pieder citam politiķim"))
        if s["third_party"]:
            out.append(Problem(ERROR, "claim", f"pozīcija {s['claim_id']} ir trešās personas komentārs, ne paša vārdi"))
        if s["review_status"] == "needs_review":
            out.append(Problem(ERROR, "claim", f"pozīcija {s['claim_id']} vēl ir pārbaudes rindā (NEEDS_REVIEW)"))
        if s["claim_type"] == "saeima_vote" and not s["vote"]:
            out.append(Problem(ERROR, "balsojums", f"balsojuma pozīcijai {s['claim_id']} nav rindas `saeima_votes`"))
        if s["vote"] and s["vote"]["own"] is None:
            out.append(Problem(ERROR, "balss", f"balsojumā {s['vote']['id']} politiķim nav balss rindas"))
        if s["claim_type"] == "position" and s["quote"] and unverbatim_quotes(f"«{s['quote']}»", s["doc_text"]):
            out.append(Problem(CHECK, "citāts", f"pozīcijas {s['claim_id']} `quote` nav burtiski avota tekstā (pārstāsts?)"))

    # Pēdiņās tikai burtiski avota vārdi.
    sources = [e.get("text", "") for e in extra_sources or []]
    for s in sides:
        sources += [s.get("stance", ""), s.get("quote", ""), s.get("doc_text", "")]
    for v in votes:
        sources += [v["motif"], v["summary"]]
    for q in unverbatim_quotes(_OTHER_QUOTES.sub(r"«\1»", summary or ""), "\n".join(sources)):
        if q in _BALLOT_WORDS:
            continue
        other = find_quote_elsewhere(db, sheet["politician_id"], q) if db is not None else None
        if other:
            out.append(Problem(CHECK, "citāts", f"«{q}» nav pretrunas abos avotos; burtiski ir {other['where']} — vai tie ir paša vārdi un vai datums tekstā sakrīt?"))
        else:
            out.append(Problem(ERROR, "citāts", f"pēdiņās ir vārdi, kuru nav burtiski ne abos avotos, ne citā šī politiķa dokumentā: «{q}»"))

    if votes:
        tallies = {t[:2] for t in (v["tally"] for v in votes)} | {v["tally"] for v in votes}
        for m in _TALLY.finditer(text):
            got = tuple(int(g) for g in m.groups() if g is not None)
            if got not in tallies:
                known = "; ".join(f"{v['date']} {v['tally'][0]}:{v['tally'][1]}:{v['tally'][2]}" for v in votes)
                out.append(Problem(CHECK, "skaits", f"«{m.group(0)}» neatbilst nevienam ķēdes balsojumam ({known})"))

        own = {v["own"] for v in votes if v["own"]}
        linked_own = {v["own"] for v in linked if v["own"]}
        if _SAID_AGAINST.search(text) and "Pret" not in own:
            out.append(Problem(CHECK, "balss", f"tekstā «balsoja pret», bet paša balsis ķēdē: {', '.join(sorted(own)) or 'nav'}"))
        if linked_own == {"Atturas"} and not _SAID_ABSTAIN.search(text):
            out.append(Problem(ERROR, "balss", "saistītajā balsojumā politiķis atturējās, bet teksts atturēšanos nemin"))
        for word in _BALLOT_WORDS:
            if f"«{word}»" in text and word not in own:
                out.append(Problem(CHECK, "balss", f"tekstā «{word}», bet paša balsis ķēdē: {', '.join(sorted(own)) or 'nav'} — vai tā ir cita cilvēka balss?"))

        if _UNANIMOUS.search(f"{summary or ''} {headline or ''}"):  # apgalvojums par frakciju parasti stāv kontekstā
            split = [v for v in linked if v["faction"]["counts"] and not _unanimous(v["faction"]["counts"])]
            for v in split:
                out.append(Problem(ERROR, "frakcija", f"teksts apgalvo vienprātību, bet balsojumā {v['id']} {v['faction']['basis']}: {_fmt_counts(v['faction']['counts'])}"))

        for s in sides:
            v = s.get("vote")
            if not v:
                continue
            mixed = {c["own"] for c in s["chain"] if c["own"] in _CAST}
            if len(mixed) > 1:
                out.append(Problem(CHECK, "ķēde", f"{v['document_nr']}: paša balsis ķēdē ir jauktas ({', '.join(sorted(mixed))}) — citē kā ķēdi vai necitē (T14)"))
            if v["motif"].lstrip().startswith("Par priekšlikumu"):
                # Priekšlikums ir saturisks grozījums, ne procedūra (#71) — bet tas ir daļa no ķēdes.
                out.append(Problem(CHECK, "priekšlikums", f"balsojums {v['id']} ir par atsevišķu priekšlikumu («{v['motif'][:80]}») — pasaki, ko priekšlikums paredzēja, un apraksti likumprojekta ķēdi (T14)"))
            elif v["procedural"]:
                out.append(Problem(CHECK, "procedūra", f"balsojums {v['id']} ir procedurāls («{v['motif'][:80]}») — tas nav politikas nostāja (T14)"))
            if v["petition"]:
                out.append(Problem(CHECK, "petīcija", f"balsojums {v['id']} ir par komisijas lēmuma projektu, ne par iesnieguma prasību (T21)"))

    known = _known_dates(sheet)
    if known:
        unquoted = re.sub(r"«[^«»]*»", " ", text)  # datums citātā ir runātāja, ne mūsu
        mentioned = {(int(m.group(2)), _MONTHS[m.group(3).lower()]): m.group(0) for m in _DATE_WORDS.finditer(unquoted)}
        mentioned.update({(int(m.group(1)), int(m.group(2))): m.group(0) for m in _DATE_NUM.finditer(unquoted) if 1 <= int(m.group(2)) <= 12})
        for key, shown in sorted(mentioned.items()):
            if key not in known:
                out.append(Problem(CHECK, "datums", f"«{shown}» nav ne pozīciju, ne balsojumu, ne avota datums — no kurienes tas ir?"))

    if headline is not None and len(headline) > 60:
        out.append(Problem(ERROR, "virsraksts", f"virsraksts {len(headline)} zīmes (≤ 60)"))
    return out


def problems_for(
    db: sqlite3.Connection,
    opponent_id: int,
    claim_old_id: int,
    claim_new_id: int,
    summary: str,
    headline: str | None = None,
    extra_sources: list[dict[str, str]] | None = None,
) -> list[Problem]:
    """Faktu lapa + pārbaude vienā solī — to sauc `store_contradiction()` un skripts."""
    sheet = fact_sheet(db, opponent_id, claim_old_id, claim_new_id)
    return check_text(sheet, summary, headline, extra_sources, db=db)


def render_sheet(sheet: dict[str, Any]) -> str:
    """Faktu lapa lasīšanai blakus kopsavilkumam."""
    lines = [f"Politiķis: {sheet['politician']} (pid {sheet['politician_id']}, partija DB: {sheet['party']})"]
    for label, s in zip(("AGRĀKĀ PUSE", "VĒLĀKĀ PUSE"), sheet["sides"], strict=True):
        lines.append("")
        if s.get("missing"):
            lines.append(f"{label}: pozīcija {s['claim_id']} neeksistē")
            continue
        lines.append(f"{label}: pozīcija {s['claim_id']} ({s['claim_type']}, {s['stated_at']})")
        lines.append(f"  avots: {s['source_url']}")
        lines.append(f"  stance: {s['stance']}")
        if s["quote"]:
            lines.append(f"  quote: {s['quote']}")
        v = s["vote"]
        if not v:
            lines.append(f"  avota teksts: {len(s['doc_text'])} zīmes, datums {s['doc_date']}")
            continue
        lines.append(f"  BALSOJUMS {v['id']} ({v['date']} {v['time'] or ''}), {v['document_nr']}: {v['motif']}")
        lines.append(f"    rezultāts: {v['result']}, par {v['tally'][0]}, pret {v['tally'][1]}, atturas {v['tally'][2]}")
        lines.append(f"    paša balss: {v['own']}")
        lines.append(f"    {v['faction']['basis']}: {_fmt_counts(v['faction']['counts'])}")
        lines.append(f"    apraksts (par likumprojektu, ne šo balsojumu — T20): {v['summary'][:400]}")
        if len(s["chain"]) > 1:
            lines.append(f"    ĶĒDE {v['document_nr']} ({len(s['chain'])} balsojumi):")
            for c in s["chain"]:
                mark = " <- šis" if c["id"] == v["id"] else ""
                lines.append(
                    f"      {c['id']} {c['date']} {c['time'] or ''} | paša: {c['own']} | {c['tally'][0]}:{c['tally'][1]}:{c['tally'][2]} "
                    f"{c['result']} | {c['faction']['basis']}: {_fmt_counts(c['faction']['counts'])} | {c['motif'][:90]}{mark}"
                )
    return "\n".join(lines)
