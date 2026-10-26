# Problem-Solving Lab

## What it does

TODO (written by student)

## Setup

Requires Python 3.13 on Windows. Commands assume PowerShell and the project root as the working directory.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` pins `chromadb==1.5.9`. The arXiv scripts use only the standard library.

## First-run downloads

The first time anything is embedded (smoke test, ingest, or the first CLI search), ChromaDB downloads the
**all-MiniLM-L6-v2** ONNX model (~79 MB) to `~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/`
(on Windows: `C:\Users\<you>\.cache\chroma\...`). Later runs use the cached copy and work offline,
except `fetch_arxiv.py --refresh`, which calls the arXiv API.

## Dataset

TODO (written by student)

## Rebuilding the corpus

`data/` is git-ignored, so a fresh clone has no database. Rebuild it in two steps:

```powershell
python fetch_arxiv.py   # 8 arXiv API queries x 50 results, 3 s apart -> data/processed/arxiv_papers.jsonl
python ingest.py        # upserts into the "papers" collection in data/chroma/
```

- `fetch_arxiv.py` caches each raw API response in `data/raw/arxiv/` and reuses it on later runs; pass `--refresh`
  to download again. It deduplicates by arXiv ID (version suffix stripped), skips empty abstracts, and aborts
  without writing anything on a network or API error.
- Expected counts from the build on 2026-10-26: 8 × 50 = 400 records returned, **399 unique papers** (one paper
  matched two queries), 0 empty abstracts. A `--refresh` run may differ slightly as arXiv's results change.
- `ingest.py` should end with `Final count in 'papers': 399`. Re-running it is safe because records are upserted by ID.
- **Truncation:** each document is the title + abstract. **152 of 399 documents (38.1%) are longer than the model's
  256-token input limit**, so their ends are cut off before embedding (about 54 tokens lost per affected document on
  average). Documents are not chunked.

Optional: `python smoke_test.py` checks the ChromaDB install using a separate `smoke_test_notes` collection.

## Running the CLI

```powershell
python cli.py
```

| Command | What it does |
|---|---|
| `search` | Prompts for a problem in everyday language and prints a Discovery Card from the top 15 results |
| `add` | Prompts for an optional title, then text; end the text with a line containing only `.`. The note is embedded and stored immediately |
| `export` | Saves the last card as Markdown in `cards/` |
| `stats` | Total count, plus counts per `source_type` and `primary_category` |
| `quit` | Exits (also `exit`, `q`, or Ctrl+Z then Enter) |

Example session:

```text
lab> search
Describe your problem: My stars move like they are following the same invisible clock; how could they behave more naturally as a group?
# Discovery Card
...
## 3. Candidate terminology (extracted from retrieved sources, approximate)
- **flocking** — in 8 sources: 2608.19887, 2609.37637, ...
- **collective motion** — in 7 sources: ...
...
lab> export
Saved ...\cards\20261026-172445-my-stars-move-like-they-are-following-th.md
lab> quit
```

Card sections: 1. your problem, 2. match strength, 3. candidate terminology, 4. discipline map, 5. potential connection,
6. sources, 7. your notes, 8. next step (a hypothesis to test).

Other scripts: `eval_queries.py` (top-10 results and distance spread for 4 test queries) and `case_evidence.py`
(shared words and closest abstract sentence for chosen queries).

## Add & search workflow

TODO (written by student)

## Vector DB & embedding model

- **Vector database:** ChromaDB 1.5.9, `chromadb.PersistentClient` storing to `data/chroma/`. `chroma.sqlite3` holds
  IDs, document text and metadata; a folder named by UUID holds the HNSW vector index for each collection.
- **Collections:** `papers` (arXiv abstracts plus user notes) and `smoke_test_notes` (12 test notes, kept separate).
- **Embedding model:** Chroma's default embedding function, `all-MiniLM-L6-v2` run locally through ONNX Runtime.
  It produces 384-dimensional vectors and truncates input at 256 tokens. It runs on CPU, with no API keys or network calls.
- **Distance:** cosine (`configuration={"hnsw": {"space": "cosine"}}`), where 0 means identical direction and
  lower means more similar. The card labels distances as strong (< 0.60), moderate (0.60–0.70) or weak (> 0.70). These bands
  were chosen from the distances seen in four test queries and are not calibrated probabilities.
- **Record IDs:** arXiv ID without the version suffix (e.g. `2106.00959`). User notes are stored as
  `note-<UTC timestamp>-<8 hex chars>`, with `source_type="user_note"`.

## Semantic search tests

TODO (written by student)

## Limitations

- **Small, narrow corpus:** 399 abstracts from 8 hand-picked queries. A problem outside collective behavior,
  multi-agent coordination, interruptions, working memory, or crowds/procedural graphics will only match weakly.
  arXiv covers psychology and the social sciences poorly.
- **Truncation:** 38% of documents lose the end of their abstract at embedding time. No chunking is done.
- **Small general-purpose model:** all-MiniLM-L6-v2 is not tuned for scientific text or for matching everyday
  phrasing to academic phrasing.
- **Uncalibrated match labels:** the strong/moderate/weak bands come from a handful of queries.
- **Heuristic terminology:** candidate terms are n-gram counts weighted by rarity across the corpus. They can include
  general words (e.g. "participants", "ordered") and miss the actual name of a field. Words from the query are removed
  using crude plural-stripping, and there is no other stemming.
- **The potential connection is only a different arXiv category** among good matches. It is not evidence that a
  mechanism transfers between fields.
- **The next-step hypothesis is a fixed template** (no LLM) and needs to be edited by the user.
- **User notes** can't be deleted from the CLI, and notes are stored with whitespace normalized (line breaks are lost).
- **Single user:** local files only, no concurrency handling.
- Stored `source_url`s keep the arXiv version suffix (`v1`) even though record IDs do not.
