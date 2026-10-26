"""Print per-result evidence for selected evaluation queries (for the write-up).

For query A (top 5) and queries C and D (top 3) prints rank, distance, title,
primary category, the non-stopword tokens shared by query and document, and
the abstract sentence closest to the query in embedding space.

Usage:
    python case_evidence.py
"""

import sys

from card import _abstract
from concepts import SENTENCE_SPLIT, match_label
from eval_queries import QUERIES, content_tokens
from lab_common import utf8_stdout
import retrieval

TOP_N = {"A": 5, "C": 3, "D": 3}


def closest_sentence(ef, query: str, text: str) -> tuple[str, float]:
    """Abstract sentence with the smallest cosine distance to the query (same embedding model)."""
    sentences = [s for s in SENTENCE_SPLIT.split(text.strip()) if s]
    vectors = ef([query] + sentences)  # MiniLM vectors are L2-normalized, so dot product = cosine
    q = vectors[0]
    distances = [1 - float(sum(a * b for a, b in zip(q, v))) for v in vectors[1:]]
    best = min(range(len(sentences)), key=distances.__getitem__)
    return sentences[best], distances[best]


def main() -> int:
    utf8_stdout()
    collection = retrieval.open_collection()
    ef = collection._embedding_function
    print(f"Collection 'papers': {collection.count()} documents")
    for label, query in QUERIES:
        if label not in TOP_N:
            continue
        query_tokens = content_tokens(query)
        print(f"\n=== Query {label} (top {TOP_N[label]})")
        print(f"Query text: {query}")
        print(f"Query content tokens: {', '.join(sorted(query_tokens))}")
        for rank, hit in enumerate(retrieval.search(collection, query, TOP_N[label]), start=1):
            shared = sorted(query_tokens & content_tokens(hit["document"]))
            sentence, s_dist = closest_sentence(ef, query, _abstract(hit))
            print(f"\n  Rank {rank}  distance={hit['distance']:.4f} ({match_label(hit['distance'])})")
            print(f"  Title: {hit['meta']['title']}")
            print(f"  Primary category: {hit['meta']['primary_category']}   id: {hit['id']}")
            print(f"  Shared non-stopword tokens: {', '.join(shared) or '(none)'}")
            print(f"  Closest abstract sentence (distance {s_dist:.4f}): {sentence}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
