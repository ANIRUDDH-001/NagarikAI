"""
Embedding Module — Phase 4
Model: sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)

Key notes:
  - This model runs on CPU locally — no GPU needed, no API cost.
  - Takes ~2 seconds to load the first time, then fast for all subsequent calls.
  - all-MiniLM-L6-v2 is optimized for semantic similarity, perfect for our RAG use case.
  - Vectors are L2-normalized so cosine similarity works correctly with pgvector.
"""
import time
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
BATCH_SIZE = 32

# --------------------------------------------------------------------------
# Load model ONCE at module startup (not on every call — this is slow).
# Any file that does `from backend.pipeline.embedder import embed_text`
# shares this single model instance.
# --------------------------------------------------------------------------
print(f"[embedder] Loading {MODEL_NAME} ...")
_model = SentenceTransformer(MODEL_NAME)
print(f"[embedder] Model loaded successfully ({EMBEDDING_DIM}-d vectors).")


def _normalize(vec: np.ndarray) -> np.ndarray:
    """L2-normalize a vector for consistent cosine similarity."""
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm


def embed_text(text: str) -> list:
    """
    Embed a single string and return a list of 384 floats (L2-normalized).
    """
    vec = _model.encode(text, convert_to_numpy=True)
    vec = _normalize(vec)
    return vec.tolist()


def embed_batch(texts: list, batch_size: int = BATCH_SIZE) -> list:
    """
    Embed multiple texts at once (much faster than one by one).
    Uses internal batching of `batch_size` for memory efficiency.
    Returns a list of lists, each containing 384 floats.
    """
    all_vecs = _model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
    # Normalize each vector
    norms = np.linalg.norm(all_vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1  # avoid division by zero
    all_vecs = all_vecs / norms
    return all_vecs.tolist()


# ---- Self-test & Benchmark ----

def _test():
    """Quick sanity check: embed one sentence, verify shape."""
    sample = "PM Kisan scheme for farmers"
    vec = embed_text(sample)
    print(f"\nTest: embed_text('{sample}')")
    print(f"  First 5 values : {vec[:5]}")
    print(f"  Dimension       : {len(vec)}  (expected {EMBEDDING_DIM})")
    assert len(vec) == EMBEDDING_DIM, f"Expected {EMBEDDING_DIM}, got {len(vec)}"
    print("  ✅ Test passed!\n")


def _benchmark(n: int = 100):
    """Time embedding `n` texts and report throughput."""
    sentences = [f"Government welfare scheme number {i}" for i in range(n)]
    start = time.perf_counter()
    embed_batch(sentences)
    elapsed = time.perf_counter() - start
    print(f"Benchmark: embedded {n} texts in {elapsed:.2f}s  "
          f"({n / elapsed:.0f} texts/sec)")


if __name__ == "__main__":
    _test()
    _benchmark()
