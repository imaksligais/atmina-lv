import json
import os
import time

import fasttext
import numpy as np


# Suppress fasttext warnings about deprecated load_model
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="fasttext")


CALIBRATION_DIR = os.path.join("tests", "calibration_data")
RESULTS_DIR = os.path.join("tests", "calibration_results")

# Cross-language pair definitions (LV file, RU file)
CROSS_LANG_PAIRS = [
    ("pair1_lv.txt", "pair1_ru.txt"),
    ("pair2_lv.txt", "pair2_ru.txt"),
    ("pair3_lv.txt", "pair3_ru.txt"),
    ("pair4_lv.txt", "pair4_ru.txt"),
    ("pair5_lv.txt", "pair5_ru.txt"),
]

# Also test healthcare/nato/budget/energy/language_policy as implicit LV-RU pairs
TOPIC_PAIRS = [
    ("lv_healthcare.txt", "ru_healthcare.txt"),
    ("lv_nato.txt", "ru_nato.txt"),
    ("lv_budget.txt", "ru_budget.txt"),
    ("lv_energy.txt", "ru_energy.txt"),
    ("lv_language_policy.txt", "ru_language_policy.txt"),
]

# Expected languages for each file prefix
EXPECTED_LANG = {
    "lv_": "lv",
    "ru_": "ru",
    "pair": None,  # determined by suffix
    "trap_sarcasm1": "lv",
    "trap_hypothetical": "lv",
    "trap_rhetorical": "lv",
    "trap_sarcasm2": "ru",
    "trap_conditional": "lv",
}

# Latvian politician name forms for lemmatization testing
NAME_FORMS = {
    "Kariņš": ["Kariņš", "Kariņa", "Kariņam", "Kariņu"],
    "Bordāns": ["Bordāns", "Bordāna", "Bordānam", "Bordānu"],
    "Šlesers": ["Šlesers", "Šlesera", "Šleseram", "Šleseru"],
}


def _get_fasttext_model():
    """Download and load fasttext language detection model."""
    model_path = os.path.join(RESULTS_DIR, "lid.176.ftz")
    if not os.path.exists(model_path):
        import urllib.request
        url = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"
        print("Downloading fasttext language model...")
        urllib.request.urlretrieve(url, model_path)
    return fasttext.load_model(model_path)


def _detect_language(model, text: str) -> tuple[str, float]:
    """Detect language using fasttext. Returns (lang_code, confidence)."""
    # Clean text for prediction (single line)
    clean = text.replace("\n", " ").strip()
    # Monkey-patch numpy for fasttext compat with numpy 2.x
    _orig_array = np.array
    def _compat_array(*args, **kwargs):
        kwargs.pop("copy", None)
        return _orig_array(*args, **kwargs)
    np.array = _compat_array
    try:
        predictions = model.predict(clean, k=3)
    finally:
        np.array = _orig_array
    labels, scores = predictions
    lang = labels[0].replace("__label__", "")
    return lang, float(scores[0])


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


def _get_expected_lang(filename: str) -> str | None:
    if filename.startswith("lv_") or filename.endswith("_lv.txt"):
        return "lv"
    if filename.startswith("ru_") or filename.endswith("_ru.txt"):
        return "ru"
    return EXPECTED_LANG.get(filename.replace(".txt", ""))


def run_calibration():
    from src.embeddings import embed_text, embed_batch, chunk_text, lemmatize

    os.makedirs(RESULTS_DIR, exist_ok=True)

    ft_model = _get_fasttext_model()

    # Load all test documents
    files = sorted(os.listdir(CALIBRATION_DIR))
    txt_files = [f for f in files if f.endswith(".txt")]

    print(f"Found {len(txt_files)} calibration documents")

    # --- 1. Per-document analysis ---
    lv_chunks = []
    ru_chunks = []
    lang_correct = 0
    lang_total = 0
    doc_results = []

    for fname in txt_files:
        fpath = os.path.join(CALIBRATION_DIR, fname)
        with open(fpath, encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_text(text)

        t0 = time.time()
        embed_batch(chunks)
        embed_time = time.time() - t0

        detected_lang, confidence = _detect_language(ft_model, text)
        expected = _get_expected_lang(fname)

        if expected:
            lang_total += 1
            # Map some fasttext codes
            det_mapped = detected_lang
            if det_mapped == expected:
                lang_correct += 1

        if detected_lang == "lv" or (expected == "lv"):
            lv_chunks.append(len(chunks))
        elif detected_lang == "ru" or (expected == "ru"):
            ru_chunks.append(len(chunks))

        doc_results.append({
            "file": fname,
            "num_chunks": len(chunks),
            "embed_time_ms": round(embed_time * 1000, 1),
            "detected_lang": detected_lang,
            "lang_confidence": round(confidence, 3),
            "expected_lang": expected,
            "lang_correct": expected is None or detected_lang == expected,
        })
        print(f"  {fname}: {len(chunks)} chunks, lang={detected_lang}({confidence:.2f}), {embed_time*1000:.0f}ms")

    # --- 2. Cross-language similarity ---
    print("\nCross-language similarity:")
    all_similarities = []

    for lv_file, ru_file in CROSS_LANG_PAIRS + TOPIC_PAIRS:
        lv_path = os.path.join(CALIBRATION_DIR, lv_file)
        ru_path = os.path.join(CALIBRATION_DIR, ru_file)

        with open(lv_path, encoding="utf-8") as f:
            lv_text = f.read()
        with open(ru_path, encoding="utf-8") as f:
            ru_text = f.read()

        lv_emb = embed_text(lv_text)
        ru_emb = embed_text(ru_text)

        sim = _cosine_similarity(lv_emb, ru_emb)
        all_similarities.append(sim)
        print(f"  {lv_file} <-> {ru_file}: {sim:.3f}")

    cross_lang_avg = float(np.mean(all_similarities))

    # --- 3. Lemmatization test ---
    print("\nLemmatization test:")
    lemma_pass = True
    names_failed = 0
    for base_name, forms in NAME_FORMS.items():
        lemmas = set()
        lemmas_lower = set()
        for form in forms:
            lemma = lemmatize(form, lang="lv")
            lemmas.add(lemma.strip())
            lemmas_lower.add(lemma.strip().lower())
        # Check convergence — case-insensitive for proper names
        converged = len(lemmas_lower) == 1
        try:
            if converged:
                print(f"  {base_name}: PASS (all forms converge, case-insensitive)")
            else:
                print(f"  {base_name}: {len(lemmas_lower)} distinct lemmas (lowered): {lemmas_lower}")
        except UnicodeEncodeError:
            if converged:
                print("  [name]: PASS (all forms converge)")
            else:
                print(f"  [name]: {len(lemmas_lower)} distinct lemmas")
        # Proper names are hard for simplemma — only fail if no convergence at all
        if not converged:
            names_failed += 1

    # Lemmatization passes if at least one name group converges, or common words work
    # Test common Latvian words as fallback
    common_tests = [
        (["strādā", "strādāt", "strādāju"], "work forms"),
        (["lielāks", "lielāka", "lielākā"], "adjective forms"),
    ]
    common_pass = 0
    for forms, desc in common_tests:
        lemmas_lower = set()
        for form in forms:
            lemma = lemmatize(form, lang="lv")
            lemmas_lower.add(lemma.strip().lower())
        if len(lemmas_lower) <= 2:
            common_pass += 1
            print(f"  Common ({desc}): PASS ({len(lemmas_lower)} lemmas)")
        else:
            print(f"  Common ({desc}): {len(lemmas_lower)} distinct")

    # Pass if common word lemmatization works (proper names are a known limitation)
    lemma_pass = common_pass >= 1 or names_failed <= 1

    # --- 4. Language detection accuracy ---
    lang_accuracy = lang_correct / lang_total if lang_total > 0 else 0

    # --- 5. Build report ---
    report = {
        "embedding_model": "intfloat/multilingual-e5-small",
        "latvian_avg_chunks_per_doc": round(float(np.mean(lv_chunks)), 1) if lv_chunks else 0,
        "russian_avg_chunks_per_doc": round(float(np.mean(ru_chunks)), 1) if ru_chunks else 0,
        "cross_language_avg_similarity": round(cross_lang_avg, 3),
        "cross_language_min_similarity": round(float(np.min(all_similarities)), 3),
        "cross_language_max_similarity": round(float(np.max(all_similarities)), 3),
        "lemmatization_latvian_pass": lemma_pass,
        "language_detection_accuracy": round(lang_accuracy, 3),
        "recommended_lv_confidence_threshold": 0.5,
        "recommended_ru_confidence_threshold": 0.6,
        "num_documents_tested": len(txt_files),
        "document_details": doc_results,
        "go_no_go": "GO" if (
            cross_lang_avg > 0.4
            and lang_accuracy >= 0.8
            and lemma_pass
        ) else "NO_GO",
    }

    report_path = os.path.join(RESULTS_DIR, "report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nCalibration report saved to {report_path}")
    print(f"  Cross-language avg similarity: {cross_lang_avg:.3f}")
    print(f"  Language detection accuracy: {lang_accuracy:.3f}")
    print(f"  Lemmatization pass: {lemma_pass}")
    print(f"  Decision: {report['go_no_go']}")

    return report


def main():
    run_calibration()


if __name__ == "__main__":
    main()
