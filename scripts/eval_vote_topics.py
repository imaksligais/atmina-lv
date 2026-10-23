"""Saeimas balsojumu tēmu klasifikatoru salīdzinājums (plāns 2026-10-21, 7. uzdevums).

Lasa `data/saeima_topic_gold/` (sample.csv, labels.csv, chain_labels.csv,
pred_*.csv) un izdrukā Markdown tabulas, no kurām salikta `ATSKAITE.md`.
DB neaiztiek, tīklu nelieto.

    PYTHONUTF8=1 .venv/Scripts/python.exe -m scripts.eval_vote_topics

Definīcijas
- `acc_doc`  = pareizi dokumenti / visi dokumenti (atturēšanās = kļūda).
- `acc_vote` = dokumenta prognoze attiecināta uz visiem tā balsojumiem,
  svari = `sample.csv:n_votes`; zelts = dokumenta etiķete.
- ķēžu `acc_vote` = dokumenta prognoze pret KATRA balsojuma zeltu
  (`chain_labels.csv`) — rāda dokumenta līmeņa metodes griestus.
- macro-F1 = vidējais F1 pār tēmām, kurām zelta atbalsts > 0.
- slieksnis: prognoze ar `confidence < t` = atturēšanās (t ietverošs: `>= t`
  paliek). Slieksni izvēlas TIKAI uz `dev`: zemākais t, pie kura dev
  precizitāte >= 0,90; ja tāda nav — t ar augstāko dev precizitāti.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

GOLD_DIR = Path(__file__).resolve().parent.parent / "data" / "saeima_topic_gold"
METHODS = ("keyword", "stored", "jev", "claude")
CONFIDENT = ("jev", "claude")
THRESHOLDS = (0.5, 0.6, 0.7, 0.8, 0.9)
PRECISION_TARGET = 0.90
BUDGET_DOCS = ("1130/Lp14", "152/Lp14")
# AUDITS.md § Aprakstīti, ne citēti — rubrika šos test dokumentus apraksta vārdos.
RUBRIC_DESCRIBED = ("215/Lp14", "561/Lp14", "219/Lm14", "876/Lp14",
                    "232/Lp14", "826/Lp14", "1073/Lp14", "44/Lp14")


def metrics(gold: dict, pred: dict, weights: dict) -> dict:
    """Rādītāji vienai metodei. Trūkstoša / None prognoze = atturēšanās (kļūda)."""
    n = len(gold)
    correct = [k for k in gold if pred.get(k) == gold[k]]
    abstain = sum(1 for k in gold if pred.get(k) is None)
    total_w = sum(weights[k] for k in gold)
    support = dict(Counter(gold.values()))
    predicted = Counter(pred[k] for k in gold if pred.get(k) is not None)
    tp = Counter(gold[k] for k in correct)
    per_topic = {}
    for t in sorted(set(support) | set(predicted)):
        p = tp[t] / predicted[t] if predicted[t] else 0.0
        r = tp[t] / support[t] if support.get(t) else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        per_topic[t] = {"p": p, "r": r, "f1": f, "support": support.get(t, 0),
                        "predicted": predicted[t], "tp": tp[t]}
    supported = list(support)
    macro = sum(per_topic[t]["f1"] for t in supported) / len(supported) if supported else 0.0
    pairs = Counter((gold[k], pred[k]) for k in gold
                    if pred.get(k) is not None and pred[k] != gold[k])
    confusion = sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))[:15]
    return {
        "n": n,
        "correct": len(correct),
        "acc_doc": len(correct) / n if n else 0.0,
        "votes": total_w,
        "votes_correct": sum(weights[k] for k in correct),
        "acc_vote": sum(weights[k] for k in correct) / total_w if total_w else 0.0,
        "macro_f1": macro,
        "macro_topics": len(supported),
        "support": support,
        "per_topic": per_topic,
        "confusion": confusion,
        "abstain": abstain,
    }


def threshold_stats(gold: dict, pred: dict, conf: dict, t: float) -> dict:
    kept = [k for k in gold if pred.get(k) is not None and conf.get(k, 0.0) >= t]
    ok = sum(1 for k in kept if pred[k] == gold[k])
    n = len(gold)
    return {"t": t, "n": n, "kept": len(kept), "ok": ok,
            "coverage": len(kept) / n if n else 0.0,
            "precision": ok / len(kept) if kept else 0.0,
            "accuracy": ok / n if n else 0.0}


def choose_threshold(rows: list[dict]) -> float:
    """rows = threshold_stats uz dev, augošā t secībā."""
    for r in rows:
        if r["kept"] and r["precision"] >= PRECISION_TARGET:
            return r["t"]
    return max(rows, key=lambda r: (r["precision"], -r["t"]))["t"]


# ---------------------------------------------------------------- CLI

def _read(name: str) -> list[dict]:
    with open(GOLD_DIR / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load() -> dict:
    sample = {r["document_key"]: r for r in _read("sample.csv")}
    labels = {r["document_key"]: r for r in _read("labels.csv")}
    chain = _read("chain_labels.csv")
    preds, confs = {}, {}
    for m in METHODS:
        rows = _read(f"pred_{m}.csv")
        preds[m] = {r["document_key"]: (r["topic"] or None) for r in rows}
        confs[m] = {r["document_key"]: float(r["confidence"]) for r in rows if r["confidence"]}
    assert set(sample) == set(labels), "sample.csv un labels.csv atslēgas atšķiras"
    for m in METHODS:
        assert set(preds[m]) == set(sample), f"pred_{m}.csv atslēgas atšķiras"
    return {"sample": sample, "labels": labels, "chain": chain, "preds": preds, "confs": confs}


def _pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.1f} %)".replace(".", ",") if b else "0/0"


def _f(x: float) -> str:
    return f"{x:.3f}".replace(".", ",")


def main() -> None:
    d = load()
    sample, labels, chain, preds, confs = d["sample"], d["labels"], d["chain"], d["preds"], d["confs"]
    gold_all = {k: r["gold_topic"] for k, r in labels.items()}
    weights = {k: int(r["n_votes"]) for k, r in sample.items()}
    split = {k: r["split"] for k, r in sample.items()}
    nesk = {k for k, r in labels.items() if r["note"].startswith("NESKAIDRS")}

    def subset(keys) -> dict:
        return {k: gold_all[k] for k in sorted(keys)}

    test = [k for k in gold_all if split[k] == "test"]
    dev = [k for k in gold_all if split[k] == "dev"]
    leak_in_test = [k for k in RUBRIC_DESCRIBED if split.get(k) == "test"]
    nesk_test = sorted(k for k in nesk if split[k] == "test")

    print("## Kopas\n")
    print(f"- dokumenti: {len(gold_all)} (test {len(test)}, dev {len(dev)}); "
          f"balsojumi pēc n_votes: {sum(weights.values())} (test {sum(weights[k] for k in test)})")
    print(f"- rubrikā aprakstītie test pusē: {len(leak_in_test)}/{len(RUBRIC_DESCRIBED)} {leak_in_test}")
    print(f"- NESKAIDRS: {len(nesk)} (test {len(nesk_test)}: {nesk_test}; "
          f"dev {sorted(k for k in nesk if split[k] == 'dev')})")
    chain_docs = sorted({r["document_key"] for r in chain})
    print(f"- ķēžu dokumenti: {len(chain_docs)}, test: "
          f"{[k for k in chain_docs if split[k] == 'test']}, dev: "
          f"{[k for k in chain_docs if split[k] == 'dev']}")
    from src.topic_map import TOPIC_GROUPS
    test_support = Counter(gold_all[k] for k in test)
    zero = sorted(t for t in TOPIC_GROUPS if test_support[t] == 0)
    print(f"- tēmas: {len(TOPIC_GROUPS)}; test atbalsts > 0: {len(TOPIC_GROUPS) - len(zero)}; "
          f"atbalsts 0: {zero}")
    unknown = {m: sorted({p for p in preds[m].values() if p and p not in TOPIC_GROUPS}) for m in METHODS}
    print(f"- nekanoniskas prognozes: {unknown}\n")

    # Sliekšņi (dev → izvēle; test → pārbaude)
    chosen = {}
    print("## Sliekšņi (t ietverošs: confidence >= t)\n")
    for m in CONFIDENT:
        print(f"### {m}\n")
        print("| t | dev segums | dev precizitāte | dev acc | test segums | test precizitāte | test acc |")
        print("|---|---|---|---|---|---|---|")
        dev_rows = []
        for t in (0.0, *THRESHOLDS):
            a = threshold_stats(subset(dev), preds[m], confs[m], t)
            b = threshold_stats(subset(test), preds[m], confs[m], t)
            if t:
                dev_rows.append(a)
            print(f"| {t:.1f} | {_pct(a['kept'], a['n'])} | {_pct(a['ok'], a['kept'])} | {_pct(a['ok'], a['n'])} "
                  f"| {_pct(b['kept'], b['n'])} | {_pct(b['ok'], b['kept'])} | {_pct(b['ok'], b['n'])} |")
        chosen[m] = choose_threshold(dev_rows)
        print(f"\nIzvēlētais slieksnis (dev): {chosen[m]:.1f}\n")

    # Galvenā tabula
    def main_table(keys, title):
        g = subset(keys)
        print(f"### {title}\n")
        print("| metode | n | acc_doc | acc_vote (n_votes) | macro-F1 | segums pie sliekšņa | precizitāte pie sliekšņa |")
        print("|---|---|---|---|---|---|---|")
        for m in METHODS:
            r = metrics(g, preds[m], weights)
            if m in chosen:
                ts = threshold_stats(g, preds[m], confs[m], chosen[m])
                cov = f"{_pct(ts['kept'], ts['n'])} (t={chosen[m]:.1f})"
                prec = _pct(ts["ok"], ts["kept"])
            else:
                cov, prec = f"{_pct(r['n'] - r['abstain'], r['n'])} (bez sliekšņa)", "—"
            print(f"| {m} | {r['n']} | {_pct(r['correct'], r['n'])} | {_pct(r['votes_correct'], r['votes'])} "
                  f"| {_f(r['macro_f1'])} ({r['macro_topics']} tēmas) | {cov} | {prec} |")
        print()

    print("## Galvenie rādītāji\n")
    main_table(test, f"test, visas rindas ({len(test)})")
    main_table([k for k in test if k not in RUBRIC_DESCRIBED],
               f"test bez rubrikā aprakstītajiem ({len(test) - len(leak_in_test)})")
    main_table([k for k in test if k not in nesk], f"test bez NESKAIDRS ({len(test) - len(nesk_test)})")
    main_table(nesk_test, f"test tikai NESKAIDRS ({len(nesk_test)})")
    main_table(dev, f"dev ({len(dev)}) — rubrikas piemēri, tikai atsaucei")

    # Ķēžu līmenis
    print("## Ķēžu līmenis: dokumenta prognoze pret katra balsojuma zeltu\n")
    print("| metode | visi balsojumi | bez budžeta ķēdēm | tikai budžeta ķēdes |")
    print("|---|---|---|---|")
    rows = {"zelta dokumenta etiķete (griesti)": gold_all, **preds}
    for name, p in rows.items():
        cells = []
        for flt in (lambda r: True, lambda r: r["document_key"] not in BUDGET_DOCS,
                    lambda r: r["document_key"] in BUDGET_DOCS):
            sel = [r for r in chain if flt(r)]
            ok = sum(1 for r in sel if p.get(r["document_key"]) == r["gold_topic"])
            cells.append(_pct(ok, len(sel)))
        print(f"| {name} | " + " | ".join(cells) + " |")
    print()

    # Sajaukšanas pāri un tēmu F1 (test)
    print("## Sajaukšanas pāri (test, zelts → prognoze, top 15)\n")
    g = subset(test)
    per = {m: metrics(g, preds[m], weights) for m in METHODS}
    for m in METHODS:
        print(f"### {m}\n")
        for (a, b), c in per[m]["confusion"]:
            print(f"- {a} → {b}: {c}")
        print()
    print("## F1 pa tēmām (test)\n")
    print("| tēma | atbalsts | " + " | ".join(METHODS) + " |")
    print("|---|---|" + "---|" * len(METHODS))
    for t in sorted(test_support, key=lambda t: (-test_support[t], t)):
        print(f"| {t} | {test_support[t]} | " +
              " | ".join(_f(per[m]["per_topic"][t]["f1"]) for m in METHODS) + " |")
    print()

    # Neatkarīgā marķētāja pārbaude: gala zelts un 1. marķētājs ir tas pats modelis
    # (claude-opus-5-5) kā Claude klasifikators, tāpēc salīdzina arī ar otro marķētāju.
    astra = {r["document_key"]: r["gold_topic"] for r in _read("labels_astra.csv")}
    print(f"## Sakritība ar otro marķētāju (gpt-6-astra, {len(astra)} test rindas, vecā rubrika 2026-10-21.1)\n")
    print("| metode | pret gala zeltu | pret otro marķētāju |")
    print("|---|---|---|")
    ga = {k: gold_all[k] for k in astra}
    for name, p in {"gala zelts": gold_all, **preds}.items():
        a = sum(1 for k in astra if p.get(k) == ga[k])
        b = sum(1 for k in astra if p.get(k) == astra[k])
        print(f"| {name} | {_pct(a, len(astra))} | {_pct(b, len(astra))} |")
    print()

    # Cena
    print("## Cena 2 583 dokumentiem\n")
    docs = 2583
    scale = docs / 253
    print(f"- Jev: $0,03 × {scale:.2f} = ${0.03 * scale:.2f}; ievade {817141 * scale:,.0f}, "
          f"izvade {108107 * scale:,.0f} tokenu (lineāra ekstrapolācija no viena skrējiena).")
    rubric_chars = len((GOLD_DIR / "RUBRIKA.md").read_text(encoding="utf-8"))
    mean_input = sum(len(r["input_text"]) for r in sample.values()) / len(sample)
    batches = -(-docs // 50)
    for cpt in (3.0, 2.5, 2.0):
        rub_tok = rubric_chars / cpt
        doc_tok = 50 * mean_input / cpt
        inp = batches * (rub_tok + doc_tok + 300)
        out_answer = docs * 40
        out_think = batches * 3000
        out = out_answer + out_think
        plain = inp * 4e-6 + out * 20e-6
        cached = (batches * (doc_tok + 300) + rub_tok * 1.25 + (batches - 1) * rub_tok * 0.05) * 4e-6 + out * 20e-6
        print(f"- Claude, {cpt} zīmes/tokenu: {batches} paketes; ievade {inp:,.0f} tokenu "
              f"(rubrika {rub_tok:,.0f}/paketē, dokumenti {doc_tok:,.0f}/paketē); izvade {out:,.0f} "
              f"(atbildes {out_answer:,} + domāšana {out_think:,}); ${plain:.2f} parasti; "
              f"rubrika kešā ${cached:.2f}; + Batch API ${cached / 2:.2f}")
    print(f"  (rubrika {rubric_chars} zīmes; vidējais input_text {mean_input:.0f} zīmes no sample.csv)")
    print("- keyword, stored: $0.")


if __name__ == "__main__":
    main()
