"""Partiju pretrunu ŠAURĀ versija — kandidātu ģenerācija (read-only).

Tvērums: partijas programmas solījums (``claim_type='program_promise'``)
pret tās FRAKCIJAS balsojuma vairākumu Saeimā. Nekas vairāk — retorikas
pret balsojumiem plašā versija ir apzināti noraidīta (BACKLOG § Partiju
pretrunas; procedurālie balsojumi + koalīcijas disciplīna ražo viltus
pozitīvos rūpnieciskā apjomā).

Šis modulis tikai ĢENERĒ kandidātus. Katrs kandidāts pirms
``store_contradiction`` iet caur @devils-advocate, izdzīvojušie —
``confirmed=0`` līdz operatora apstiprinājumam (eskalācija 3). Kandidātu
ģenerācija ir strukturāls SQL — embeddings šeit NEKUR nav ceļā (T9/T10).

Cietie vārti (secībā): T14 procedurālais veto → tēmas sakritība →
frakcijas nostājas blīvums (≥60 % no kastajām balsīm). Ex-ST ierobežojums:
kopš ~2026-04-16 ST frakcijas avotā nav, tāpēc tās solījumiem kandidāti
pēc tā datuma nav aprēķināmi pēc konstrukcijas (izmeklēts 2026-08-06).

Plāns: docs/plans/2026-08-06-partiju-pretrunu-saura-versija.md.
"""

from __future__ import annotations

import math
import re
import sqlite3
import struct
from typing import Any, Optional

# T14: procedurāls motīvs NEKAD nevar būt pretrunas pamats. References ķēde:
# 2025-04-10 Krievijas/Baltkrievijas tirdzniecības aizlieguma darba kārtības
# balsojums (atturas) + tas pats projekts komisijai (PAR) vienā minūtē.
PROCEDURAL_MOTIF_RE = re.compile(
    r"iekļaušan\w*\s+.*darba\s+kārtīb"
    r"|nodošan\w*\s+.*komisij"
    r"|nodošana\s+komisijām"
    r"|steidzam"
    r"|priekšlikumu\s+Nr\s*\.",
    re.IGNORECASE | re.DOTALL,
)

# Balsis, kas ir nostāja; Nebalsoja/Reģistrējies/... NAV
# (reference_saeima_vote_values + CLAUDE.md Atturas noteikums).
_CAST = ("Par", "Pret", "Atturas")

# Frakcijas nostājai vajag vismaz šādu īpatsvaru no kastajām balsīm —
# zem tā frakcija ir šķelta un nostājas nav (plāna 60/40 slieksnis).
MAJORITY_THRESHOLD = 0.6


def is_procedural(motif: Optional[str]) -> bool:
    """T14 veto — True, ja balsojuma motīvs ir procedurāls."""
    return bool(motif and PROCEDURAL_MOTIF_RE.search(motif))


def faction_stance(
    db: sqlite3.Connection, vote_id: int, faction: str
) -> Optional[dict[str, Any]]:
    """Frakcijas nostāja VIENĀ balsojumā vai None.

    Autoritāte ir ``saeima_individual_votes.faction`` TAJĀ balsojumā (T6
    korolārs) — nekad ``tracked_politicians.party`` grupējums. None, ja
    frakcijai balsojumā nav kastu balsu (t.sk. ex-ST NULL gadījums) vai
    sadalījums ir zem MAJORITY_THRESHOLD.
    """
    rows = db.execute(
        "SELECT vote, COUNT(*) c FROM saeima_individual_votes "
        "WHERE vote_id = ? AND faction = ? AND vote IN (?, ?, ?) "
        "GROUP BY vote",
        (vote_id, faction, *_CAST),
    ).fetchall()
    counts = {r["vote"]: r["c"] for r in rows}
    cast = sum(counts.values())
    if cast == 0:
        return None
    top_vote, top_n = max(counts.items(), key=lambda kv: kv[1])
    if top_n / cast < MAJORITY_THRESHOLD:
        return None  # šķelta frakcija — nostājas nav
    return {"stance": top_vote, "counts": counts, "cast": cast}


def document_chain(db: sqlite3.Connection, document_nr: str) -> list[dict[str, Any]]:
    """Visi balsojumi ar šo ``document_nr`` — T14 ķēdes lasīšanai."""
    rows = db.execute(
        "SELECT id, vote_date, vote_time, motif, total_par, total_pret, "
        "total_atturas, result FROM saeima_votes WHERE document_nr = ? "
        "ORDER BY vote_date, vote_time",
        (document_nr,),
    ).fetchall()
    return [dict(r) for r in rows]


def generate_candidates(db: sqlite3.Connection) -> dict[str, Any]:
    """Kandidātu saraksts + godīgi denominatori.

    Kandidāts = (solījums, balsojums, frakcijas nostāja) vienā tēmā, kas
    izgājis T14 veto un blīvuma slieksni. Virziena spriedums (vai nostāja
    tiešām ir PRET solījumu) ir @devils-advocate satura darbs, ne šī SQL.
    """
    parties = db.execute(
        "SELECT id, name, short_name FROM parties WHERE id IN "
        "(SELECT DISTINCT party_id FROM claims WHERE claim_type='program_promise')"
    ).fetchall()

    stats = {
        "parties_with_program": len(parties),
        "parties_with_faction_votes": 0,
        "promises_seen": 0,
        "votes_considered": 0,
        "vetoed_procedural": 0,
        "no_faction_stance": 0,
        "candidates": 0,
    }
    out: list[dict[str, Any]] = []

    for party in parties:
        faction = party["short_name"]
        has_votes = db.execute(
            "SELECT 1 FROM saeima_individual_votes WHERE faction = ? LIMIT 1",
            (faction,),
        ).fetchone()
        if not has_votes:
            continue  # ārpus-Saeimas partija — kandidātu nav pēc konstrukcijas
        stats["parties_with_faction_votes"] += 1

        promises = db.execute(
            "SELECT id, topic, stance, source_url FROM claims "
            "WHERE claim_type='program_promise' AND party_id = ?",
            (party["id"],),
        ).fetchall()
        stats["promises_seen"] += len(promises)

        for promise in promises:
            votes = db.execute(
                "SELECT DISTINCT sv.id, sv.motif, sv.vote_date, sv.document_nr, "
                "sv.url, sv.result FROM saeima_votes sv "
                "JOIN claims c ON c.source_url = sv.url "
                "WHERE c.claim_type='saeima_vote' AND c.topic = ?",
                (promise["topic"],),
            ).fetchall()
            for vote in votes:
                stats["votes_considered"] += 1
                if is_procedural(vote["motif"]):
                    stats["vetoed_procedural"] += 1
                    continue
                fs = faction_stance(db, vote["id"], faction)
                if fs is None:
                    stats["no_faction_stance"] += 1
                    continue
                stats["candidates"] += 1
                out.append({
                    "party": party["name"],
                    "faction": faction,
                    "promise_id": promise["id"],
                    "promise_topic": promise["topic"],
                    "promise_stance": promise["stance"],
                    "promise_url": promise["source_url"],
                    "vote_id": vote["id"],
                    "vote_date": vote["vote_date"],
                    "motif": vote["motif"],
                    "document_nr": vote["document_nr"],
                    "faction_stance": fs["stance"],
                    "faction_counts": fs["counts"],
                    "vote_url": vote["url"],
                    "chain_len": len(document_chain(db, vote["document_nr"]))
                    if vote["document_nr"] else 0,
                })

    return {"stats": stats, "candidates": out}


# ---------------------------------------------------------------------------
# Ranžēšana (piltuves (i) posms — operatora verdikts 2026-08-17)
#
# Tēmas līmeņa pārošana viena pati pārģenerē (18 914 pāri; 1 807 pēc
# Pret/Atturas ekrāna), jo kanoniskās tēmas ir platas. Šis posms sakārto tos
# pēc SATURA tuvības BEZ aģentiem un BEZ jaunas embedēšanas: lasa jau
# esošos ``claim_vectors`` abām pusēm. Rangs NAV spriedums par pretrunu —
# tas ir tikai DA budžeta sadales kārtība (T9/T10: embedding nekad neredz
# stance neatbilstību; virziena spriedums paliek @devils-advocate).
# ---------------------------------------------------------------------------

COSINE_WEIGHT = 0.75
LEXICAL_WEIGHT = 0.25

# Balsojuma motīvu veidlapa — šie stumbri ir gandrīz katrā motīvā, tāpēc
# leksiskajā pārklājumā tie mērītu formu, ne saturu.
# (stumbri _STEM_LEN garumā; "likum" sedz arī "likumprojekta")
_BOILERPLATE_STEMS = {
    "grozī", "likum", "lasīj", "saeim", "proje", "lēmum", "priek", "panta",
    "progr", "pared", "solīt", "solīj", "iebil", "atbal", "sēdes",
}
_WORD_RE = re.compile(r"[a-zA-ZāčēģīķļņōŗšūžĀČĒĢĪĶĻŅŌŖŠŪŽ]{5,}")
_BOILER_LEN = 5   # veidlapas atpazīšanai (sedz "likumā"/"likumprojekta")
_STEM_LEN = 6     # sakritības stumbram — 5 zīmes sapludina "civilprocesa"
                  # ar "civildienesta" (reāls FP 2026-08-18 palaidienā)
# Motīvs mēdz būt 1–2 satura vārdi; bez saucēja grīdas viens sakritis vārds
# uzreiz dotu 1.0 un izspiestu bagātākus pārus.
_MIN_DENOM = 3


def ensure_vec(db: sqlite3.Connection) -> None:
    """Ielādē sqlite_vec šajā savienojumā (``claim_vectors`` ir vec0 tabula)."""
    import sqlite_vec

    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)


def load_claim_vector(db: sqlite3.Connection, claim_id: int) -> Optional[list[float]]:
    """Esošais claim vektors vai None — NEKAD neembedē no jauna."""
    ensure_vec(db)
    row = db.execute(
        "SELECT embedding FROM claim_vectors WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if row is None or row[0] is None:
        return None
    blob = bytes(row[0])
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


def cosine(a: list[float], b: list[float]) -> float:
    """Kosinusa tuvība. Garumu nesakritība = kļūda, ne klusa 0.0."""
    if len(a) != len(b):
        raise ValueError(f"vektoru garumi atšķiras: {len(a)} != {len(b)}")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _stems(text: str) -> set[str]:
    out = set()
    for word in _WORD_RE.findall(text or ""):
        low = word.lower()
        if low[:_BOILER_LEN] in _BOILERPLATE_STEMS:
            continue
        out.add(low[:_STEM_LEN])
    return out


def lexical_overlap(a: str, b: str) -> float:
    """Pārklājuma koeficients pār satura vārdu stumbriem (0..1).

    Otrais, lēts signāls blakus kosinusam: solījuma teksts ir garš, motīvs
    īss, tāpēc Žakāra koeficients sistemātiski nenovērtētu kopīgo priekšmetu
    — lietojam |A∩B| / max(_MIN_DENOM, min(|A|,|B|)). Veidlapas stumbri
    izmesti.
    """
    sa, sb = _stems(a), _stems(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(_MIN_DENOM, min(len(sa), len(sb)))


def score_pair(cos: float, lex: float, topic_match: bool) -> float:
    """Rangs = tēmas sakritība × (0.75·kosinuss + 0.25·leksiskais).

    Tēmas sakritība ir REIZINĀTĀJS, nevis saskaitāmais: tēma ir ciets vārts
    (plāna 2. vārti), un reizinātājs padara neiespējamu, ka augsts kosinuss
    ievelk cross-topic pāri. Kosinuss dominē, jo tas ir vienīgais semantiskais
    signāls; leksiskais pārklājums tikai šķir vienādi tuvus pārus par labu
    tiem, kam sakrīt burtiskais priekšmets.
    """
    if not topic_match:
        return 0.0
    return COSINE_WEIGHT * cos + LEXICAL_WEIGHT * lex


def representative_vote_claim(
    db: sqlite3.Connection,
    vote_url: str,
    topic: str,
    vote_id: int,
    faction: str,
    stance: str,
) -> Optional[int]:
    """Frakcijas deputāta ``saeima_vote`` claim ID šim balsojumam un tēmai.

    Plāna datu modelis: ``claim_id_2`` = REPREZENTATĪVS frakcijas deputāta
    balsojuma claim. Priekšroka deputātam, kurš balsoja tieši frakcijas
    nostāju; ja politiķu sasaiste balsojumā trūkst, atkāpjas uz jebkuru šī
    URL + tēmas balsojuma claim (teksts ir tas pats motīvs).
    """
    row = db.execute(
        "SELECT MIN(c.id) FROM claims c WHERE c.claim_type='saeima_vote' "
        "AND c.source_url = ? AND c.topic = ? AND c.opponent_id IN ("
        "  SELECT politician_id FROM saeima_individual_votes "
        "  WHERE vote_id = ? AND faction = ? AND vote = ? "
        "  AND politician_id IS NOT NULL)",
        (vote_url, topic, vote_id, faction, stance),
    ).fetchone()
    if row and row[0]:
        return int(row[0])
    row = db.execute(
        "SELECT MIN(id) FROM claims WHERE claim_type='saeima_vote' "
        "AND source_url = ? AND topic = ?",
        (vote_url, topic),
    ).fetchone()
    return int(row[0]) if row and row[0] else None


def rank_candidates(
    db: sqlite3.Connection,
    candidates: list[dict[str, Any]],
    top_n: int = 30,
    collapse_chains: bool = True,
) -> dict[str, Any]:
    """Sakārto kandidātus pēc satura tuvības. READ-ONLY — neko neraksta.

    ``collapse_chains``: viena ``document_nr`` ķēde ir VIENS DA spriedums
    (T14 — ķēde jālasa kopā), tāpēc pa noklusējumam no katra
    ``(promise_id, document_nr)`` pāra paliek augstākais rangs; pārējie tiek
    saskaitīti ``collapsed_chain_dupes``, saucējs ``ranked`` paliek pilns.

    Atgriež ``{"ranked": [...top_n...], "stats": {...saucēji...}}``.
    """
    stats = {
        "pairs_in": len(candidates),
        "vetoed_procedural": 0,
        "no_vote_claim": 0,
        "skipped_missing_vector": 0,
        "ranked": 0,
        "collapsed_chain_dupes": 0,
        "top_n": top_n,
    }
    scored: list[dict[str, Any]] = []
    vec_cache: dict[int, Optional[list[float]]] = {}

    def _vec(claim_id: int) -> Optional[list[float]]:
        if claim_id not in vec_cache:
            vec_cache[claim_id] = load_claim_vector(db, claim_id)
        return vec_cache[claim_id]

    for cand in candidates:
        # Otrais T14 slānis: ekrāns to jau izmet, bet ranžētājs nedrīkst
        # atgriezt procedurālu pāri arī tad, ja to padod tieši.
        if is_procedural(cand.get("motif")):
            stats["vetoed_procedural"] += 1
            continue
        vote_claim_id = representative_vote_claim(
            db, cand["vote_url"], cand["promise_topic"], cand["vote_id"],
            cand["faction"], cand["faction_stance"],
        )
        if vote_claim_id is None:
            stats["no_vote_claim"] += 1
            continue
        pv, vv = _vec(cand["promise_id"]), _vec(vote_claim_id)
        if pv is None or vv is None:
            # Trūkstošs vektors NAV 0.0 tuvība — tas ir izlaists pāris.
            stats["skipped_missing_vector"] += 1
            continue
        vote_topic = db.execute(
            "SELECT topic FROM claims WHERE id = ?", (vote_claim_id,)
        ).fetchone()[0]
        cos = cosine(pv, vv)
        lex = lexical_overlap(cand["promise_stance"], cand.get("motif") or "")
        score = score_pair(cos, lex, topic_match=vote_topic == cand["promise_topic"])
        stats["ranked"] += 1
        scored.append({
            **cand,
            "vote_claim_id": vote_claim_id,
            "cosine": cos,
            "lexical": lex,
            "score": score,
        })

    scored.sort(key=lambda c: (-c["score"], c["promise_id"], c["vote_id"]))

    if collapse_chains:
        seen: set[tuple] = set()
        kept: list[dict[str, Any]] = []
        for c in scored:
            key = (c["promise_id"], c["document_nr"] or f"vote:{c['vote_id']}")
            if key in seen:
                stats["collapsed_chain_dupes"] += 1
                continue
            seen.add(key)
            kept.append(c)
        scored = kept

    return {"stats": stats, "ranked": scored[:top_n]}
