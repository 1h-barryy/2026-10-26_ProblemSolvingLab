"""Run informal evaluation queries against the "papers" collection.

For each query prints the top 10 hits (rank, distance, paper_id, primary
category, title, and non-stopword tokens shared by query and document), then
the distribution of top-10 distances to help pick a cutoff later.

Usage:
    python eval_queries.py
"""

import re
import statistics
import sys

import chromadb

from lab_common import DB_DIR, PAPERS_COLLECTION, embedding_function, utf8_stdout

TOP_K = 10

QUERIES = [
    ("A", "My stars move like they are following the same invisible clock; "
          "how could they behave more naturally as a group?"),
    ("B", "When I come back to something after doing other things, I lose track of where I was."),
    # Backups: one per case family, same informal style.
    ("C", "The fake crowds in my game all walk in straight lines and pile up at doorways."),
    ("D", "Every time a notification pops up I get distracted and it takes ages to focus again."),
]

STOPWORDS = set("""
a about above after again against all am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further get gets got
had has have having he her here hers him his how i if in into is it its itself just me more most my
myself no nor not now of off on once only or other our ours out over own same she should so some
such than that the their theirs them then there these they this those through to too under until up
very was we were what when where which while who whom why will with would you your yours
also like thing things using use used based we our paper show propose study results
""".split())
TOKEN = re.compile(r"[a-z0-9]+")


def content_tokens(text: str) -> set[str]:
    return {t for t in TOKEN.findall(text.lower()) if t not in STOPWORDS and len(t) > 1}


def main() -> int:
    utf8_stdout()
    client = chromadb.PersistentClient(path=str(DB_DIR))
    collection = client.get_collection(PAPERS_COLLECTION, embedding_function=embedding_function())
    print(f"Collection '{PAPERS_COLLECTION}': {collection.count()} documents\n")

    all_distances: dict[str, list[float]] = {}
    for label, query in QUERIES:
        results = collection.query(query_texts=[query], n_results=TOP_K,
                                   include=["documents", "metadatas", "distances"])
        query_tokens = content_tokens(query)
        print(f"=== Query {label}: {query}")
        print(f"    content tokens: {', '.join(sorted(query_tokens))}")
        rows = zip(results["distances"][0], results["metadatas"][0], results["documents"][0])
        for rank, (distance, meta, doc) in enumerate(rows, start=1):
            shared = sorted(query_tokens & content_tokens(doc))
            print(f"{rank:>3}. {distance:.4f}  {meta['paper_id']:<18} {meta['primary_category']:<12} "
                  f"{meta['title'][:90]}")
            print(f"{'':>13}shared: {', '.join(shared) or '(none)'}")
        all_distances[label] = results["distances"][0]
        print()

    print("=== Top-10 distance distribution (cosine distance; lower = more similar)")
    print(f"{'query':<6} {'rank1':>7} {'rank2':>7} {'rank5':>7} {'rank10':>7} {'mean':>7} {'stdev':>7} "
          f"{'r1-r2 gap':>9}")
    for label, d in all_distances.items():
        print(f"{label:<6} {d[0]:>7.4f} {d[1]:>7.4f} {d[4]:>7.4f} {d[-1]:>7.4f} "
              f"{statistics.mean(d):>7.4f} {statistics.stdev(d):>7.4f} {d[1] - d[0]:>9.4f}")
    pooled = sorted(x for d in all_distances.values() for x in d)
    quartiles = statistics.quantiles(pooled, n=4)
    print(f"pooled (n={len(pooled)}): min={pooled[0]:.4f} q1={quartiles[0]:.4f} "
          f"median={quartiles[1]:.4f} q3={quartiles[2]:.4f} max={pooled[-1]:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
