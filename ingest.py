"""Load data/processed/arxiv_papers.jsonl into the persistent "papers" collection.

One record per paper: document = title + blank line + abstract. Upsert by
paper_id makes re-runs safe. Also reports how many documents exceed the
embedding model's 256-token input limit (those are silently truncated by the
model; this phase does not chunk).

Usage:
    python ingest.py
"""

import json
import sys
from pathlib import Path

import chromadb
from tokenizers import Tokenizer

from lab_common import (COLLECTION_CONFIG, DB_DIR, MODEL_MAX_TOKENS, PAPERS_COLLECTION,
                        PAPERS_JSONL, clean, embedding_function, utf8_stdout)

BATCH_SIZE = 64
TOKENIZER_PATH = Path.home() / ".cache" / "chroma" / "onnx_models" / "all-MiniLM-L6-v2" / "onnx" / "tokenizer.json"


def load_papers() -> list[dict]:
    with PAPERS_JSONL.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def to_document(paper: dict) -> str:
    return clean(paper["title"]) + "\n\n" + clean(paper["abstract"])


def to_metadata(paper: dict) -> dict:
    return {
        "paper_id": paper["paper_id"],
        "title": paper["title"],
        "primary_category": paper["primary_category"],
        "categories": ",".join(paper["categories"]),
        "published": paper["published"],
        "source_url": paper["source_url"],
        "source_type": "arxiv",
    }


def report_token_lengths(documents: list[str]) -> None:
    if not TOKENIZER_PATH.exists():
        print(f"\nTokenizer not found at {TOKENIZER_PATH}; skipping token-length report.")
        return
    # Fresh tokenizer with no truncation, so we see the true length. Counts include [CLS] and [SEP].
    tokenizer = Tokenizer.from_file(str(TOKENIZER_PATH))
    tokenizer.no_truncation()
    tokenizer.no_padding()
    lengths = sorted(len(enc.ids) for enc in tokenizer.encode_batch(documents))
    over = [n for n in lengths if n > MODEL_MAX_TOKENS]
    print(f"\nToken lengths (all-MiniLM-L6-v2 tokenizer, incl. [CLS]/[SEP]): "
          f"min={lengths[0]} median={lengths[len(lengths) // 2]} max={lengths[-1]}")
    print(f"Documents over {MODEL_MAX_TOKENS} tokens (truncated at embedding time): "
          f"{len(over)} of {len(lengths)} ({100 * len(over) / len(lengths):.1f}%)")
    if over:
        lost = sum(n - MODEL_MAX_TOKENS for n in over)
        print(f"  tokens cut off across those documents: {lost} "
              f"(mean {lost / len(over):.0f} per truncated document)")


def main() -> int:
    utf8_stdout()
    if not PAPERS_JSONL.exists():
        print(f"ERROR: {PAPERS_JSONL} not found. Run fetch_arxiv.py first.", file=sys.stderr)
        return 1
    papers = load_papers()
    documents = [to_document(p) for p in papers]
    print(f"Loaded {len(papers)} papers from {PAPERS_JSONL.name}")

    client = chromadb.PersistentClient(path=str(DB_DIR))
    collection = client.get_or_create_collection(
        name=PAPERS_COLLECTION,
        configuration=COLLECTION_CONFIG,
        embedding_function=embedding_function(),
    )
    config = collection.configuration
    print(f"Collection '{PAPERS_COLLECTION}': space={config['hnsw']['space']}, "
          f"embedding_function={config['embedding_function'].name()}")
    smoke = client.get_collection("smoke_test_notes")
    print(f"Collection 'smoke_test_notes' (for comparison): space={smoke.configuration['hnsw']['space']}, "
          f"embedding_function={smoke.configuration['embedding_function'].name()}")
    print(f"Count before upsert: {collection.count()}")

    for start in range(0, len(papers), BATCH_SIZE):
        batch = papers[start:start + BATCH_SIZE]
        collection.upsert(
            ids=[p["paper_id"] for p in batch],
            documents=documents[start:start + BATCH_SIZE],
            metadatas=[to_metadata(p) for p in batch],
        )
        print(f"  upserted {start + len(batch)}/{len(papers)}")

    print(f"Final count in '{PAPERS_COLLECTION}': {collection.count()}")
    report_token_lengths(documents)
    return 0


if __name__ == "__main__":
    sys.exit(main())
