"""Persistent ChromaDB smoke test.

Stores ~12 temporary research-topic notes in a local, on-disk ChromaDB
collection, runs a few semantic similarity queries, and reports whether the
collection already existed from a previous run (i.e. whether it persisted).

These documents are throwaway test data, not the research corpus.

Usage:
    python smoke_test.py            # create/update and query
    python smoke_test.py --reset    # delete the collection first, then rebuild
"""

import argparse
from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError

DB_DIR = Path(__file__).resolve().parent / "data" / "chroma"
COLLECTION_NAME = "smoke_test_notes"

# Stable, hand-assigned IDs: re-running upserts the same 12 records instead of
# appending duplicates.
SAMPLE_NOTES = [
    ("note-001", "biology",
     "Flocks of starlings form murmurations where each bird reacts only to its nearest neighbors, "
     "yet the whole group moves as one fluid shape."),
    ("note-002", "computer-graphics",
     "Boids is a simulation model in which agents follow separation, alignment, and cohesion rules "
     "to produce lifelike flocking animation."),
    ("note-003", "robotics",
     "Swarm robotics coordinates many simple robots through local communication rather than a "
     "central controller."),
    ("note-004", "psychology",
     "Task switching imposes a cognitive cost: people respond more slowly and make more errors "
     "right after changing from one task to another."),
    ("note-005", "psychology",
     "Attention residue describes how thoughts about an unfinished task persist and reduce "
     "performance on the next task."),
    ("note-006", "hci",
     "Interruption studies in human-computer interaction measure how long knowledge workers take "
     "to resume a primary task after a notification."),
    ("note-007", "ecology",
     "Predator-prey dynamics can be modeled with coupled differential equations such as the "
     "Lotka-Volterra system."),
    ("note-008", "economics",
     "Information cascades occur when individuals ignore their private information and copy the "
     "decisions of people who acted before them."),
    ("note-009", "physics",
     "Phase transitions in the Vicsek model show how self-propelled particles shift from "
     "disordered motion to collective alignment as noise decreases."),
    ("note-010", "neuroscience",
     "Working memory has limited capacity, and maintaining goals across delays depends on "
     "prefrontal cortex activity."),
    ("note-011", "materials-science",
     "Crystalline lattices form when atoms settle into repeating low-energy arrangements during "
     "slow cooling."),
    ("note-012", "urban-planning",
     "Pedestrian crowd simulations use social force models to predict congestion at exits and "
     "intersections."),
]

QUERIES = [
    "my animated particles move too robotically, how do real groups of animals move together?",
    "I lose my train of thought when I get pulled away from a task and struggle to get back into it",
    "how do many simple machines cooperate without a leader?",
]


def collection_exists(client: chromadb.ClientAPI, name: str) -> bool:
    try:
        client.get_collection(name)
        return True
    except NotFoundError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="delete the collection before running")
    args = parser.parse_args()

    DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(DB_DIR))
    print(f"ChromaDB {chromadb.__version__} | storage: {DB_DIR}")

    if args.reset and collection_exists(client, COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
        print(f"--reset: deleted collection '{COLLECTION_NAME}'")

    existed = collection_exists(client, COLLECTION_NAME)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        configuration={"hnsw": {"space": "cosine"}},
    )
    count_before = collection.count()
    print(f"\n[persistence] collection existed before this run: {existed}")
    print(f"[persistence] documents already stored on disk:   {count_before}")

    # upsert = insert new IDs, overwrite existing IDs. Safe to repeat.
    collection.upsert(
        ids=[note_id for note_id, _, _ in SAMPLE_NOTES],
        documents=[text for _, _, text in SAMPLE_NOTES],
        metadatas=[{"field": field, "source": "smoke_test"} for _, field, _ in SAMPLE_NOTES],
    )
    count_after = collection.count()
    print(f"[persistence] documents after upsert:             {count_after}")
    if count_after != len(SAMPLE_NOTES):
        print(f"[warning] expected {len(SAMPLE_NOTES)} documents, found {count_after}")

    for query in QUERIES:
        results = collection.query(
            query_texts=[query],
            n_results=3,
            include=["documents", "metadatas", "distances"],
        )
        print(f"\nQuery: {query!r}")
        hits = zip(
            results["ids"][0],
            results["distances"][0],
            results["metadatas"][0],
            results["documents"][0],
        )
        for rank, (doc_id, distance, meta, doc) in enumerate(hits, start=1):
            print(f"  {rank}. {doc_id}  distance={distance:.4f}  field={meta['field']}")
            print(f"     {doc}")

    print("\nDone. Run again: 'existed before this run' should be True and the count should stay "
          f"at {len(SAMPLE_NOTES)}.")


if __name__ == "__main__":
    main()
