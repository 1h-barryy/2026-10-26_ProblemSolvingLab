"""Access to the persistent "papers" collection: search, add notes, stats."""

import uuid
from collections import Counter
from datetime import datetime, timezone

import chromadb

from lab_common import COLLECTION_CONFIG, DB_DIR, PAPERS_COLLECTION, clean, embedding_function


def open_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(DB_DIR))
    return client.get_or_create_collection(
        name=PAPERS_COLLECTION,
        configuration=COLLECTION_CONFIG,
        embedding_function=embedding_function(),
    )


def search(collection: chromadb.Collection, query: str, k: int = 15) -> list[dict]:
    """Return the top-k hits, best first, as dicts with id/distance/metadata/document."""
    results = collection.query(query_texts=[query], n_results=k,
                               include=["documents", "metadatas", "distances"])
    return [
        {"id": doc_id, "distance": dist, "meta": meta, "document": doc}
        for doc_id, dist, meta, doc in zip(results["ids"][0], results["distances"][0],
                                           results["metadatas"][0], results["documents"][0])
    ]


def all_documents(collection: chromadb.Collection) -> list[str]:
    return collection.get(include=["documents"])["documents"]


def add_note(collection: chromadb.Collection, text: str, title: str = "") -> str:
    """Embed and store a user note immediately. Returns its new ID."""
    now = datetime.now(timezone.utc)
    note_id = f"note-{now.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    text = clean(text)
    title = clean(title)
    collection.add(
        ids=[note_id],
        documents=[f"{title}\n\n{text}" if title else text],
        metadatas=[{
            "paper_id": note_id,
            "title": title or "(untitled note)",
            "primary_category": "user_note",
            "categories": "",
            "published": "",
            "source_url": "",
            "source_type": "user_note",
            "created_at": now.isoformat(timespec="seconds"),
        }],
    )
    return note_id


def stats(collection: chromadb.Collection) -> dict:
    metas = collection.get(include=["metadatas"])["metadatas"]
    return {
        "total": len(metas),
        "by_category": Counter(m.get("primary_category", "?") for m in metas),
        "by_source_type": Counter(m.get("source_type", "?") for m in metas),
    }
