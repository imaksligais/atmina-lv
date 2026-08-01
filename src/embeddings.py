import threading

import simplemma

_model = None
_model_lock = threading.Lock()
_MODEL_NAME = "intfloat/multilingual-e5-small"


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(_MODEL_NAME)
    return _model


def chunk_text(text: str, max_tokens: int = 400, overlap: int = 80) -> list[str]:
    import logging
    logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)
    model = _get_model()
    tokenizer = model.tokenizer
    tokens = tokenizer.encode(text, add_special_tokens=False)

    if len(tokens) <= max_tokens:
        return [text]

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text_str = tokenizer.decode(chunk_tokens, skip_special_tokens=True)
        chunks.append(chunk_text_str)
        if end >= len(tokens):
            break
        start += max_tokens - overlap

    return chunks


def embed_text(text: str) -> list[float]:
    model = _get_model()
    prefixed = f"query: {text}"
    embedding = model.encode(prefixed, normalize_embeddings=True)
    return embedding.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    prefixed = [f"passage: {t}" for t in texts]
    embeddings = model.encode(prefixed, normalize_embeddings=True)
    return [e.tolist() for e in embeddings]


def embed_document(text: str) -> list[tuple[int, str, list[float]]]:
    chunks = chunk_text(text)
    embeddings = embed_batch(chunks)
    return [(i, chunk, emb) for i, (chunk, emb) in enumerate(zip(chunks, embeddings))]


def lemmatize(text: str, lang: str = "lv") -> str:
    words = text.split()
    lemmas = [simplemma.lemmatize(word, lang=lang) for word in words]
    return " ".join(lemmas)
