"""`scripts/eval_vote_topics.py` — tīrā metriku loģika (plāns 2026-10-21, 7. uzdevums).

Kļūme, ko tests ķer: nepareizs saucējs (trūkstoša prognoze izkrīt no `n`, nevis
skaitās par atturēšanos), svari neietekmē `acc_vote`, vai macro-F1 vidējo ņem
pār tēmām bez atbalsta zelta kopā.
"""
from scripts.eval_vote_topics import metrics


def test_metrics_counts_and_macro_f1():
    gold = {"a": "X", "b": "X", "c": "Y"}
    pred = {"a": "X", "b": "Y", "c": "Y"}
    weights = {"a": 1, "b": 1, "c": 10}
    m = metrics(gold, pred, weights)
    assert m["n"] == 3 and m["acc_doc"] == 2 / 3
    assert m["acc_vote"] == 11 / 12
    assert round(m["macro_f1"], 3) == round((2 / 3 + 2 / 3) / 2, 3)
    assert m["support"] == {"X": 2, "Y": 1}


def test_metrics_missing_prediction_counts_as_abstain():
    m = metrics({"a": "X"}, {}, {"a": 1})
    assert m["abstain"] == 1 and m["acc_doc"] == 0


def test_macro_f1_ignores_zero_support_topic():
    # Kļūdaina prognoze tēmā Z (zelta atbalsts 0) bojā precizitāti un accuracy,
    # bet Z netiek iekļauta macro-F1 vidējā.
    m = metrics({"a": "X", "b": "X"}, {"a": "X", "b": "Z"}, {"a": 1, "b": 1})
    assert set(m["per_topic"]) >= {"X"}
    assert round(m["macro_f1"], 3) == round(2 / 3, 3)
    assert m["confusion"] == [(("X", "Z"), 1)]
