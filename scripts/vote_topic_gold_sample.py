"""Zelta kopas izlase Saeimas balsojumu tēmām (plāns 2026-10-21, 4. uzdevums).

Lasa dzīvo DB TIKAI lasīšanas režīmā un uzraksta `data/saeima_topic_gold/sample.csv`
ar kolonnām: document_key, prefix, n_votes, current_topic, stratum, split,
input_text, input_hash. Deterministisks: `random.Random(20261021)`, visas kopas
pirms izlozes sakārtotas.

Atslēgas
--------
Balsojumus grupē pēc `src.saeima.topics.document_key(document_nr, motif)`.
- `None` atslēga (kails numurs, ko motīvs neatrisina) — izlaista; skaitu izdrukā.
- `reason='multi'` (motīvā vairāki numuri, piem. «… likumprojekta (Nr.1225/Lp14) …
  (957/Lm14)») — izlaista; atslēgas izdrukā. Ielādē tām klasifikators atsakās
  (8. uzd.: lēmums tikai ar roku), tāpēc zelta etiķete tur neko nemērītu.
- `motif:<sha1>` (`reason='no-number'`) — paliek; tā ir atsevišķā josla bez numura.

`current_topic` = biežākā `saeima_votes.topic` atslēgas balsojumos (neizšķirts →
alfabētiski pirmā). TIKAI stratifikācijai: to NEKAD nepadod klasifikatoram vai
marķētājam (Global Constraints: pašreizējās tēmas nenonāk promptos).

`prefix` ∈ Lp / Lm / P / other (no atslēgas; `motif:` → other).

`input_text`
------------
Rindas ar latviskiem marķieriem:
- «Virsraksts:» — motīvs līdz pirmajam «(NNN/XxNN)», bez sākuma procedūras
  frāzēm («Par priekšlikumu Nr.N.», «Par likumprojekta atzīšanu par steidzamu.»);
  atslēgas balsojumu biežākais variants (neizšķirts → īsākais, tad alfabētiski).
  `motif:` atslēgām — viss motīvs.
- «Kopsavilkums:» — atšķirīgie `summary` (līdz 3) pēc pirmā balsojuma id secības,
  katrs nogriezts līdz 600 zīmēm.
- «Likumprojekts:» / «Likumprojekta kopsavilkums:» — `saeima_bills.title/summary`,
  ja `saeima_bills.document_nr` = atslēga (citādi pēc balsojumu biežākā `bill_id`);
  rindu izlaiž, ja tā burtiski atkārto virsrakstu vai kādu jau iekļautu kopsavilkumu.
Tēmas (`saeima_votes.topic`, `saeima_bills.topic`) input_text NEKAD neietver.
`input_hash` = sha1(input_text.encode("utf-8")).

Stratu prioritāte (fiksēta; atslēga saņem PIRMĀ izvēlējušā strata vārdu)
----------------------------------------------------------------------
1. `rare`  — visas atslēgas ar `current_topic`, kurā < 15 atslēgu.
2. `chain` — 20 atslēgas ar ≥ 10 balsojumiem, tikai numurētās (`motif:` ķēdēs visi
   balsojumi ir viens motīvs — vote≠document tur nav ko mērīt): obligāti 1286/Lp14
   (specifikācijas zināmais vote≠document gadījums), pārējās 19 izlozē.
3. `motif` — 20 nejaušas `motif:` atslēgas.
4. `vp`    — papildina līdz 70 NUMURĒTĀM atslēgām ar `current_topic`='Valsts pārvalde'
   (jau izvēlētās skaitās; `motif:` josla ir atsevišķa, tāpēc neskaitās).
5. `vide`  — tāpat līdz 25 numurētām «Vide».
6. `prefix` — papildina katru prefiksu (P, Lm, Lp) līdz ≥ 20; ņem tikai no tēmām,
   kas nav rare / VP / Vide, lai 4.–5. kvotas paliek precīzas.
7. `prop`  — atlikums līdz 250, proporcionāli atslēgu skaitam pārējās tēmās
   (lielākā atlikuma metode; jau izvēlētās skaitās).

`split`: dev/test 40/60, grupējot pēc bāzes likuma: teksts pēc «Grozījum(i|s)» līdz
«likumā» (ieskaitot pēdiņu formu «likumā “Par …”»), citādi pats virsraksts; «likum*»
galotnes saplūdina (jauns «Sporta likums» = «Grozījumi Sporta likumā»). Grupas
nejaušā secībā, retāko tēmu grupas vispirms, katra iet tajā pusē, kura ir
tālāk no sava mērķa — tā viena likuma grozījumi nekad nav abās pusēs. Grupas, kurās
ir kaut viena RUBRIKA.md robežpiemērā citēta atslēga, iet uz `dev` (rubrika nonāk
klasifikatora promptā, tātad tās atslēgām etiķete ir zināma); ja kāda citēta atslēga
nonāk `test`, skripts apstājas ar kļūdu.

Palaišana: `.venv/Scripts/python.exe scripts/vote_topic_gold_sample.py [--db ...] [--out ...]`
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.saeima.topics import (  # noqa: E402
    compose_input_text,
    document_key,
    document_title,
)

SEED = 20261021
TOTAL = 250
RARE_LT = 15
N_CHAIN, CHAIN_MIN_VOTES = 20, 10
FORCED_CHAINS = ("1286/Lp14",)  # ietilpst 20: nejauši izlozē tikai 20 - len(FORCED_CHAINS)
N_MOTIF = 20
VP, N_VP = "Valsts pārvalde", 70
VIDE, N_VIDE = "Vide", 25
PREFIX_MIN = 20
DEV_SHARE = 0.4

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO / "data" / "atmina.db"
DEFAULT_OUT = REPO / "data" / "saeima_topic_gold" / "sample.csv"
DEFAULT_RUBRIC = REPO / "data" / "saeima_topic_gold" / "RUBRIKA.md"
_CITED_RE = re.compile(r"\b\d+/(?:Lp|Lm|P)\d+\b")
COLUMNS = ["document_key", "prefix", "n_votes", "current_topic", "stratum", "split",
           "input_text", "input_hash"]

_BASE_LAW = re.compile(r"Grozījum\w*\s+(.*?likumā(?:\s*[“\"«][^”\"»]+[”\"»])?)",
                       re.IGNORECASE)


def _prefix(key: str) -> str:
    if key.startswith("motif:"):
        return "other"
    return re.sub(r"\d+$", "", key.split("/", 1)[1])


def _base_group(title: str) -> str:
    m = _BASE_LAW.search(title)
    text = m.group(1) if m else title
    text = re.sub(r"[“”\"«»„]", "", text).lower().strip()
    # «Sporta likums» (jauns likums) un «Grozījumi Sporta likumā» = viena grupa.
    return re.sub(r"\blikum\w*", "likum", text)


def load(db: sqlite3.Connection):
    votes = defaultdict(list)  # key -> [(id, motif, topic, summary, bill_id)]
    skipped_none, multi = 0, []
    for vid, nr, motif, topic, summary, bill_id in db.execute(
            "SELECT id, document_nr, motif, topic, summary, bill_id FROM saeima_votes"
            " ORDER BY id"):
        key, reason = document_key(nr, motif)
        if key is None:
            skipped_none += 1
            continue
        if reason == "multi":
            multi.append(key)
            continue
        votes[key].append((vid, motif or "", topic, summary, bill_id))
    bills_by_nr = {r[0]: (r[1], r[2]) for r in db.execute(
        "SELECT document_nr, title, summary FROM saeima_bills")}
    bills_by_id = {r[0]: (r[1], r[2]) for r in db.execute(
        "SELECT id, title, summary FROM saeima_bills")}
    return votes, skipped_none, sorted(set(multi)), bills_by_nr, bills_by_id


def build_doc(key, rows, bills_by_nr, bills_by_id) -> dict:
    topics = Counter(r[2] for r in rows)
    top_n = max(topics.values())
    current = sorted(t for t, n in topics.items() if n == top_n)[0]
    titles = Counter(document_title(r[1], key) for r in rows)
    best = max(titles.values())
    title = sorted((t for t, n in titles.items() if n == best), key=lambda t: (len(t), t))[0]
    summaries: list[str] = []
    for r in rows:  # rows ir id secībā
        s = (r[3] or "").strip()
        if s and s not in summaries:
            summaries.append(s)
    bill = bills_by_nr.get(key)
    if bill is None:
        ids = Counter(r[4] for r in rows if r[4] is not None)
        if ids:
            bill = bills_by_id.get(sorted(ids.items(), key=lambda kv: (-kv[1], kv[0]))[0][0])
    # Forma kopīga ar ielādi (`src.saeima.topics.compose_input_text`).
    text = compose_input_text(title, summaries, bill)
    return {"document_key": key, "prefix": _prefix(key), "n_votes": len(rows),
            "current_topic": current, "title": title, "input_text": text,
            "input_hash": hashlib.sha1(text.encode("utf-8")).hexdigest()}


def select(docs: dict[str, dict], rng: random.Random) -> dict[str, str]:
    """Atgriež {atslēga: stratum} pēc fiksētās prioritātes (sk. moduļa docstring)."""
    keys = sorted(docs)
    per_topic = Counter(docs[k]["current_topic"] for k in keys)
    rare_topics = {t for t, n in per_topic.items() if n < RARE_LT}
    chosen: dict[str, str] = {}

    def take(pool, n, stratum):
        pool = [k for k in pool if k not in chosen]
        for k in rng.sample(pool, max(0, min(n, len(pool)))):
            chosen[k] = stratum

    def numbered(topic):
        return [k for k in keys if docs[k]["prefix"] != "other"
                and docs[k]["current_topic"] == topic]

    for k in keys:
        if docs[k]["current_topic"] in rare_topics:
            chosen[k] = "rare"
    forced = [k for k in FORCED_CHAINS if k in docs and k not in chosen]
    for k in forced:  # zināmais vote≠document gadījums (spec § Dati)
        chosen[k] = "chain"
    take([k for k in keys if docs[k]["prefix"] != "other"
          and docs[k]["n_votes"] >= CHAIN_MIN_VOTES], N_CHAIN - len(forced), "chain")
    take([k for k in keys if docs[k]["prefix"] == "other"], N_MOTIF, "motif")
    for topic, n, stratum in ((VP, N_VP, "vp"), (VIDE, N_VIDE, "vide")):
        have = sum(1 for k in chosen if k in numbered(topic))
        take(numbered(topic), n - have, stratum)
    quota_topics = rare_topics | {VP, VIDE}
    for pfx in ("P", "Lm", "Lp"):
        have = sum(1 for k in chosen if docs[k]["prefix"] == pfx)
        take([k for k in keys if docs[k]["prefix"] == pfx
              and docs[k]["current_topic"] not in quota_topics], PREFIX_MIN - have, "prefix")
    # Proporcionālais atlikums (lielākā atlikuma metode) pārējām tēmām.
    rest = sorted(t for t in per_topic if t not in quota_topics)
    have_rest = Counter(docs[k]["current_topic"] for k in chosen
                        if docs[k]["current_topic"] in rest)
    budget = TOTAL - len(chosen) + sum(have_rest.values())
    if budget > 0:
        total_rest = sum(per_topic[t] for t in rest)
        exact = {t: budget * per_topic[t] / total_rest for t in rest}
        alloc = {t: int(exact[t]) for t in rest}
        for t in sorted(rest, key=lambda t: (-(exact[t] - alloc[t]), t))[
                :budget - sum(alloc.values())]:
            alloc[t] += 1
        for t in rest:
            take([k for k in keys if docs[k]["current_topic"] == t],
                 alloc[t] - have_rest[t], "prop")
    return chosen


def assign_split(docs, chosen, rng, cited=frozenset()) -> dict[str, str]:
    groups = defaultdict(list)
    for k in sorted(chosen):
        groups[_base_group(docs[k]["title"])].append(k)
    topic_n = Counter(docs[k]["current_topic"] for k in chosen)
    order = sorted(groups)
    rng.shuffle(order)
    order.sort(key=lambda g: min(topic_n[docs[k]["current_topic"]] for k in groups[g]))
    target = {"dev": DEV_SHARE, "test": 1 - DEV_SHARE}
    filled = {"dev": 0, "test": 0}
    filled_topic = {"dev": Counter(), "test": Counter()}
    split = {}

    def score(side, g, gt):
        # Cik pārpildīta būtu puse pēc grupas pievienošanas: katrā grupas tēmā
        # (pret tēmas mērķi) + kopumā (pret kopējo mērķi).
        s = sum(n * (filled_topic[side][t] + n) / (target[side] * topic_n[t])
                for t, n in gt.items())
        return s + (filled[side] + len(groups[g])) / (target[side] * len(chosen))

    # Grupas ar RUBRIKA.md citētu atslēgu → dev (rubrikas piemērs = etiķetes
    # mājiens promptā; `test` tādu nedrīkst saturēt). Tās iet pirmās.
    order.sort(key=lambda g: not any(k in cited for k in groups[g]))
    for g in order:
        gt = Counter(docs[k]["current_topic"] for k in groups[g])
        if any(k in cited for k in groups[g]):
            side = "dev"
        else:
            side = min(("dev", "test"), key=lambda s: (score(s, g, gt), s))
        for k in groups[g]:
            split[k] = side
        filled[side] += len(groups[g])
        filled_topic[side].update(gt)
    return split, groups


def _table(title, counter, targets=None):
    print(f"\n{title}")
    for name in sorted(counter, key=lambda x: (-counter[x], x)):
        tgt = f"   (mērķis {targets[name]})" if targets and name in targets else ""
        print(f"  {counter[name]:>4}  {name}{tgt}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--rubric", default=str(DEFAULT_RUBRIC))
    args = ap.parse_args(argv)

    db = sqlite3.connect(f"file:{Path(args.db).as_posix()}?mode=ro", uri=True)
    votes, skipped_none, multi, bills_by_nr, bills_by_id = load(db)
    docs = {k: build_doc(k, rows, bills_by_nr, bills_by_id) for k, rows in votes.items()}
    rng = random.Random(SEED)
    chosen = select(docs, rng)
    rubric = Path(args.rubric)
    if not rubric.exists():
        raise SystemExit(f"KĻŪDA: nav rubrikas {rubric} (vajag citēto atslēgu sarakstam)")
    cited = frozenset(_CITED_RE.findall(rubric.read_text(encoding="utf-8")))
    split, groups = assign_split(docs, chosen, rng, cited)
    leaked = sorted(k for k in chosen if k in cited and split[k] == "test")
    if leaked:
        raise SystemExit(f"KĻŪDA: RUBRIKA.md citētas atslēgas test pusē: {leaked}")

    # Sargi: tukšs input_text, dublikāti, grupa abās pusēs.
    errors = [k for k in chosen if not docs[k]["input_text"].strip()]
    if errors:
        raise SystemExit(f"KĻŪDA: tukšs input_text atslēgām {errors}")
    rows = [{**{c: docs[k][c] for c in COLUMNS if c in docs[k]},
             "stratum": chosen[k], "split": split[k]} for k in sorted(chosen)]
    dup = [k for k, n in Counter(r["document_key"] for r in rows).items() if n > 1]
    if dup:
        raise SystemExit(f"KĻŪDA: dublētas atslēgas {dup}")
    for g, ks in groups.items():
        if len({split[k] for k in ks}) > 1:
            raise SystemExit(f"KĻŪDA: grupa {g!r} abās pusēs")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    per_topic_all = Counter(d["current_topic"] for d in docs.values())
    rare = {t for t, n in per_topic_all.items() if n < RARE_LT}
    print(f"Dzīvā DB: {len(docs)} atslēgas; izlaistas: None={skipped_none} balsojumi, "
          f"multi={len(multi)} {multi}")
    print(f"KOPĀ izlasē: {len(rows)} (mērķis ~{TOTAL}); grupas pēc bāzes likuma: {len(groups)}")
    _table("Pa stratum:", Counter(r["stratum"] for r in rows),
           {"rare": f"visas {sum(per_topic_all[t] for t in rare)}", "chain": N_CHAIN,
            "motif": N_MOTIF})
    _table("Pa prefiksu (kopā):", Counter(r["prefix"] for r in rows),
           {p: f">={PREFIX_MIN}" for p in ("Lp", "Lm", "P")} | {"other": N_MOTIF})
    _table("Pa split:", Counter(r["split"] for r in rows),
           {"dev": f"~{round(DEV_SHARE * len(rows))}",
            "test": f"~{len(rows) - round(DEV_SHARE * len(rows))}"})
    numbered_vp = sum(1 for r in rows if r["current_topic"] == VP and r["prefix"] != "other")
    numbered_vide = sum(1 for r in rows if r["current_topic"] == VIDE and r["prefix"] != "other")
    print(f"\nNumurētās VP: {numbered_vp} (mērķis {N_VP}); numurētās Vide: {numbered_vide} "
          f"(mērķis {N_VIDE}); VP kopā ar motif: "
          f"{sum(1 for r in rows if r['current_topic'] == VP)}")
    chain_rows = [r for r in rows if r["stratum"] == "chain"]
    long_rows = [r for r in rows if r["n_votes"] >= CHAIN_MIN_VOTES]
    print(f"Ķēdes: stratum=chain {len(chain_rows)}, balsojumu summa {sum(r['n_votes'] for r in chain_rows)}"
          f" (5. uzd. etiķetes katram); visas izlases atslēgas ar ≥{CHAIN_MIN_VOTES}: {len(long_rows)}")
    print(f"1286/Lp14 izlasē: {'jā' if '1286/Lp14' in chosen else 'nē'}")
    # RUBRIKA.md robežpiemēri ar numuru = etiķetes mājiens klasifikatora promptā.
    hit = Counter(split[k] for k in chosen if k in cited)
    print(f"RUBRIKA.md citētās atslēgas izlasē: {sum(hit.values())} no {len(cited)} "
          f"(dev {hit['dev']}, test {hit['test']})")
    targets = {t: f"visi {per_topic_all[t]}" for t in rare} | {VP: N_VP, VIDE: N_VIDE}
    by_topic = Counter(r["current_topic"] for r in rows)
    print("\nPa current_topic (izlase / visas DB atslēgas; TIKAI stratifikācijai):")
    for t in sorted(per_topic_all, key=lambda x: (-by_topic[x], x)):
        tgt = f"   (mērķis {targets[t]})" if t in targets else ""
        print(f"  {by_topic[t]:>4} / {per_topic_all[t]:>4}  {t}{tgt}")
    split_topic = Counter((r["current_topic"], r["split"]) for r in rows)
    print("\nPa current_topic × split (dev/test):")
    for t in sorted(by_topic, key=lambda x: (-by_topic[x], x)):
        print(f"  {split_topic[(t, 'dev')]:>3}/{split_topic[(t, 'test')]:<3} {t}")
    print(f"\nUzrakstīts: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
