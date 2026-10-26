"""Shared paths and small helpers for the Problem-Solving Lab scripts."""

import io
import sys
from pathlib import Path

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

ROOT = Path(__file__).resolve().parent
DB_DIR = ROOT / "data" / "chroma"
RAW_DIR = ROOT / "data" / "raw" / "arxiv"
PAPERS_JSONL = ROOT / "data" / "processed" / "arxiv_papers.jsonl"

PAPERS_COLLECTION = "papers"
# Same settings smoke_test.py ended up with: Chroma's default embedding
# function (all-MiniLM-L6-v2 via ONNX, 384 dims) and cosine distance.
COLLECTION_CONFIG = {"hnsw": {"space": "cosine"}}
MODEL_MAX_TOKENS = 256  # Chroma truncates MiniLM input at 256 word-pieces


def embedding_function() -> DefaultEmbeddingFunction:
    return DefaultEmbeddingFunction()


def utf8_stdout() -> None:
    """Avoid UnicodeEncodeError on Windows consoles/pipes (abstracts contain non-ASCII)."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8", errors="replace")


def clean(text: str | None) -> str:
    """Collapse line breaks and runs of whitespace."""
    return " ".join((text or "").split())
