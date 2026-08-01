"""Partiju pretrunu šaurās versijas piltuve (READ-ONLY, atkārtojama).

Šis skripts ir VISA piltuve līdz @devils-advocate pakāpei. Tas NEKO neraksta
DB — nulle ``store_contradiction`` izsaukumu pēc nodoma (plāna 4. solis ir
atsevišķs, operatora apstiprināts solis).

    .venv/Scripts/python.exe scripts/partiju_pretrunas.py            # kandidāti
    .venv/Scripts/python.exe scripts/partiju_pretrunas.py --rank     # + rangs
    .venv/Scripts/python.exe scripts/partiju_pretrunas.py --rank --top 30 \
        --out docs/eval/party_funnel_2026-08-18.md

PILNĀ PROCEDŪRA (operatora verdikts 2026-08-17 — piltuves dizains apstiprināts
ar nosacījumu "darbojas nākotnē + efficient"):

1. KANDIDĀTU ĢENERĀCIJA (strukturāls SQL, ``generate_candidates``):
   partijas programmas solījums × tās FRAKCIJAS balsojuma vairākums vienā
   kanoniskā tēmā. Cietie vārti secībā: T14 procedurālais veto → tēmas
   sakritība → frakcijas nostājas blīvums ≥60 % no kastajām balsīm.
   Noklusētais Pret/Atturas ekrāns ir rupjš neatbilstības filtrs (``--all``
   to noņem). Ex-ST ierobežojums: kopš ~2026-04-16 frakcijas avotā nav.

2. RANGS BEZ AĢENTIEM (``--rank``, ``rank_candidates``): katram pārim
   kosinusa tuvība starp solījuma un REPREZENTATĪVĀ frakcijas deputāta
   balsojuma claim JAU ESOŠAJIEM ``claim_vectors`` (nekas netiek embedēts no
   jauna; trūkstošs vektors = izlaists pāris ar uzskaiti, NEVIS 0.0 tuvība)
   + leksiskais pārklājums pār satura vārdu stumbriem. Rangs =
   tēmas_sakritība × (0.75·kosinuss + 0.25·leksiskais). Vienas ``document_nr``
   ķēdes pāri saspiesti vienā (T14 — ķēde lasāma kopā; ``--no-collapse``
   atslēdz). Rangs NAV spriedums par pretrunu — T9/T10: embedding stance
   neatbilstību neredz. Tas ir tikai DA budžeta sadales kārtība.

3. @devils-advocate PA VIENAM PĀRIM top ~30 sarakstā, ar BINĀRO vārtu:
   KILL vai KEEP. Downgrade/"vājāks formulējums" NAV atļauta izvēle —
   verify-lēcas sistemātiski izvēlas downgrade, kad vārti nav bināri.
   Ieejas artefakts DA dispatcham ir tieši šī skripta markdown izvade.

4. IZDZĪVOJUŠIE → ``store_contradiction(..., confirmed=0, party_id=...)``,
   ``claim_id_1`` = programmas solījums, ``claim_id_2`` = ``vote_claim_id``
   no izvades. Bez izņēmumiem confirmed=0 (eskalācija 3).

5. OPERATORA REVIEW → tikai pēc tā render partijas lapas "Programma" sadaļā.

Saucēji (cik pāru ienāca, cik ar vektoriem, cik izlaisti, top-N) tiek
izdrukāti KATRĀ palaidienā — vārts bez saucēja nav pierādījums.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_db  # noqa: E402
from src.party_contradictions import (  # noqa: E402
    COSINE_WEIGHT,
    LEXICAL_WEIGHT,
    generate_candidates,
    rank_candidates,
)


def _markdown(gen_stats: dict, rank_stats: dict, ranked: list[dict],
              screened: int) -> str:
    lines = [
        "# Partiju pretrunu piltuve — ranžēts DA saraksts",
        "",
        "Read-only izvade. Nekas nav glabāts DB (0 `store_contradiction`).",
        f"Rangs = tēmas sakritība × ({COSINE_WEIGHT}·kosinuss + "
        f"{LEXICAL_WEIGHT}·leksiskais pārklājums), abas puses no jau esošajiem "
        "`claim_vectors`.",
        "",
        "## Saucēji",
        "",
        "| Posms | Skaits |",
        "|---|---|",
    ]
    for k, v in gen_stats.items():
        lines.append(f"| ģenerācija: {k} | {v} |")
    lines.append(f"| Pret/Atturas ekrāns | {screened} |")
    for k, v in rank_stats.items():
        lines.append(f"| rangs: {k} | {v} |")
    lines += [
        "",
        "## Top pāri (@devils-advocate — BINĀRS vārts: KILL vai KEEP)",
        "",
    ]
    for i, c in enumerate(ranked, 1):
        lines += [
            f"### {i}. {c['party']} ({c['faction']}) — {c['promise_topic']} "
            f"· rangs {c['score']:.3f}",
            "",
            f"- **Solījums** (claim #{c['promise_id']}): {c['promise_stance']}",
            f"  - avots: {c['promise_url']}",
            f"- **Balsojums** {c['vote_date']} (vote #{c['vote_id']}, "
            f"dok. {c['document_nr']}, ķēdē {c['chain_len']}): frakcija "
            f"**{c['faction_stance']}** {c['faction_counts']}",
            f"  - motīvs: {c['motif']}",
            f"  - avots: {c['vote_url']}",
            f"  - reprezentatīvais balsojuma claim: #{c['vote_claim_id']}",
            f"- tuvība: kosinuss {c['cosine']:.3f} · leksiskais "
            f"{c['lexical']:.3f}",
            "",
        ]
    if not ranked:
        lines.append("_Nulle ranžētu pāru ir derīgs iznākums._")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="partiju pretrunu piltuve (read-only)")
    ap.add_argument("--json", action="store_true", help="JSON izvade")
    ap.add_argument("--all", action="store_true",
                    help="rādīt arī Par nostājas (noklusēti tikai Pret/Atturas — "
                         "rupjš neatbilstības ekrāns; virziena spriedums paliek DA)")
    ap.add_argument("--rank", action="store_true",
                    help="piltuves (i) posms: satura rangs pēc esošajiem "
                         "claim_vectors, markdown DA dispatcham")
    ap.add_argument("--top", type=int, default=30, help="cik pāru izvadē (rangam)")
    ap.add_argument("--no-collapse", action="store_true",
                    help="nesaspiest vienas document_nr ķēdes pārus vienā DA "
                         "spriedumā (noklusēti saspiež — T14 ķēde lasāma kopā)")
    ap.add_argument("--out", type=Path, default=None,
                    help="rakstīt markdown failā (noklusēti stdout)")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    db = get_db()
    result = generate_candidates(db)
    shown = result["candidates"] if args.all else [
        c for c in result["candidates"] if c["faction_stance"] in ("Pret", "Atturas")
    ]

    if args.rank:
        ranking = rank_candidates(db, shown, top_n=args.top,
                                  collapse_chains=not args.no_collapse)
        if args.json:
            print(json.dumps({"gen_stats": result["stats"],
                              "rank_stats": ranking["stats"],
                              "ranked": ranking["ranked"]},
                             ensure_ascii=False, indent=1))
            return
        md = _markdown(result["stats"], ranking["stats"], ranking["ranked"],
                       len(shown))
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(md, encoding="utf-8")
            print(f"Ierakstīts: {args.out}")
            # Atslēgas prefiksētas: abiem posmiem ir "vetoed_procedural", un
            # nesaliktā apvienošana klusi pārrakstīja ģenerācijas saucēju ar
            # ranga nulli — saucējs, kas pazūd, ir tas pats defekts, ko šie
            # saucēji sargā.
            print("== Saucēji ==")
            for k, v in result["stats"].items():
                print(f"  ģenerācija.{k}: {v}")
            print(f"  ekrāns.pret_atturas: {len(shown)}")
            for k, v in ranking["stats"].items():
                print(f"  rangs.{k}: {v}")
        else:
            print(md)
        return

    if args.json:
        print(json.dumps({"stats": result["stats"], "candidates": shown},
                         ensure_ascii=False, indent=1))
        return

    s = result["stats"]
    print("== Denominatori ==")
    for k, v in s.items():
        print(f"  {k}: {v}")
    if not args.all:
        print(f"  rādīti (Pret/Atturas ekrāns): {len(shown)}")
    print()
    print("== Kandidāti (virziena spriedums = @devils-advocate darbs) ==")
    for c in shown:
        print(f"- {c['party']} ({c['faction']}) · solījums #{c['promise_id']} "
              f"[{c['promise_topic']}] pret balsojumu {c['vote_id']} "
              f"({c['vote_date']}, {c['document_nr']}, ķēdē {c['chain_len']}): "
              f"frakcija {c['faction_stance']} {c['faction_counts']}")
        print(f"    solījums: {c['promise_stance'][:120]}")
        print(f"    motīvs:   {(c['motif'] or '')[:120]}")


if __name__ == "__main__":
    main()
