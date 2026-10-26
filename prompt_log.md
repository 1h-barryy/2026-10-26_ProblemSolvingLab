# Prompt log

## AI Tool Used

ChatGPT 6 Astra
Claude Opus5.5
Claude code Opus 5.5

## Prompt 

### Brain storming prompt


I personally prefer ideas 2 and 6, although I think ideas 1 and 2 have more research potential.

The first idea reminds me of a financial game I worked on previously. I eventually realized that it didn't have much practical use or meaning beyond demonstrating the concept.

However, idea 2 also feels somewhat like Wikipedia. I want to explore how we could make it more meaningful.



I think I would actually use this app, although making it genuinely useful would probably require several iterations and a much more complete database.

For now, our main goal is to finish and submit the assignment.

I really like the Problem-Solving Lab concept, but I'm also thinking about its target audience. If someone isn't a researcher or designer, would they actually ask questions about academic mechanisms or cross-disciplinary approaches?

I also want to explore adding AI and RAG in future iterations, but that doesn't need to be part of the current assignment.



I'm happy with the current scope and overall design direction.

However, I want to refine the core interaction. Instead of simply asking a problem and receiving possible solutions, I want users to describe their problems in natural language.

The app should help identify and categorize the professional or academic terminology behind those problems. It should also help users discover related concepts or analogies from other disciplines.

I think this should be the central experience of the application.



  ### 1. Project Setup

  You are currently working in this project repo

  - Use Python.
  - Set up a virtual environment.
  - Install ChromaDB.
  - Create a minimal `requirements.txt`.
  - Create a `.gitignore` that excludes virtual environments, local vector database files, downloaded datasets, caches, and secrets.
  - Do not modify other existing projects.

  ### 2. Persistent ChromaDB Smoke Test

  Create a small script called `smoke_test.py`.

  Requirements:

  - Use `chromadb.PersistentClient`.
  - Store database files in a local directory.
  - Create a dedicated collection named `smoke_test_notes`.
  - Add approximately 10–12 temporary sample documents representing different research topics.
  - Use unique document IDs and make the test safe to run repeatedly without accidentally duplicating entries.
  - Execute at least two semantic similarity queries.
  - Display retrieved documents, IDs, and distances.
  - Confirm that the collection persists after the script exits and is run again.

  These temporary documents are only for testing. They are not the final research corpus.

  ### 3. Inspect the Real Dataset

  Create a separate script named `preview_arxiv.py`.

  Use the public arXiv API to retrieve a small sample of research paper metadata.

  Start with a topic related to collective behavior, swarm intelligence, or human-computer interaction.

  For each retrieved paper, inspect:

  - Paper ID
  - Title
  - Abstract
  - Primary academic category
  - Additional categories, if available
  - Source URL
  - Publication date
  - Approximate abstract length

  Only retrieve a few records in this phase.

  Use reasonable network timeouts and respect API usage limits. Handle network errors gracefully. Do not fabricate papers if the API is unavailable.

  Do not ingest the full dataset into ChromaDB yet.

  ### 4. Initial Project Notes

  Create a short `PROJECT_NOTES.md` containing:

  - The project's product goal.
  - The proposed document structure.
  - The fact that each real database item will represent a research abstract or an appropriately sized excerpt.
  - Two provisional natural-language semantic search cases:

  Case A: A user describes computer-generated particles moving too mechanically and wants to understand natural group movement.

  Case B: A user describes having difficulty returning to a task after switching attention away from it.

  For each case, list some possible academic research concepts worth testing.

  Clearly label these as hypotheses, not verified retrieval results.

  ## Constraints

  - No LLM integration.
  - No RAG generation.
  - No frontend or web UI.
  - No large-scale dataset ingestion yet.
  - Do not build the final Concept Mapping system yet.
  - Do not write a final README describing features that have not been implemented.
  - Keep the project modular and easy to extend.
  - Use currently supported ChromaDB APIs.

  ## Verification

  After implementation:

  1. Run the smoke test.
  2. Run it a second time to verify persistence.
  3. Run the arXiv preview script.
  4. Report the actual observed results, including any failures.
  5. Explain the created file structure.
  6. Explain briefly how ChromaDB stores documents, embeddings, and metadata.

  Stop after this phase. Do not proceed to Phase 2 automatically.

  I want to inspect the implementation and understand the database behavior before we expand the project.


   real corpus + retrieval evaluation. Deadline is tonight, keep it simple and don't build the CLI yet.

  1. fetch_arxiv.py
     - Run ~8 arXiv API queries, 50 results each, sleep 3s between requests.
     - Query mix (adjust syntax as needed):
       cat:nlin.AO; all:"collective motion" OR all:flocking; cat:cs.MA AND all:coordination;
       all:"swarm robotics"; cat:cs.HC AND (all:interruption OR all:resumption);
       cat:q-bio.NC AND all:"working memory"; cat:cs.GR AND (all:procedural OR all:crowd);
       cat:q-bio.PE AND all:"collective behavior"
     - Cache raw responses under data/raw/ (git-ignored). Dedupe by arXiv ID with the version suffix stripped.
       Skip records with empty abstracts. Fail loudly on network errors; never invent records.
     - Print per-query counts, total unique count, and abstract word-length stats.
  2. ingest.py
     - New persistent collection named "papers", separate from the smoke test collection.
       Use the same embedding function and explicitly set cosine space; confirm what smoke_test.py used.
     - document = title + "\n\n" + abstract (whitespace normalized).
     - metadata: paper_id, title, primary_category, categories (comma-joined string), published, source_url, source_type="arxiv".
     - Upsert in batches; print the final count.
     - Using the model's tokenizer if accessible, report how many documents exceed 256 tokens (they will be truncated). Do not chunk.
  3. eval_queries.py
     - Run these queries against "papers" and print the top 10 for each: rank, distance, paper_id, primary_category, title,
       and the non-stopword tokens shared between the query and the document.
       A: "My stars move like they are following the same invisible clock; how could they behave more naturally as a group?"
       B: "When I come back to something after doing other things, I lose track of where I was."
       Plus 2 backup queries of your choice in the same informal style.
     - Also print the distance distribution of the top 10 so we can choose a cutoff later.

  Put stdout UTF-8 reconfiguration inside the scripts. Report the actual outputs. Don't interpret beyond what the numbers show, and stop after this phase.


   an interactive CLI with a Discovery Card, runtime insertion, and persistence. No LLM. Keep heuristics simple and transparent. Small modules are fine (retrieval.py, concepts.py, card.py, cli.py) but don't over-engineer.

  CLI (cli.py), commands:
  - search: user types an everyday-language problem -> prints a Discovery Card
  - add: user pastes a note or abstract (multi-line, optional title) -> embedded immediately, id like note-<timestamp>-<short-uuid>,
    metadata source_type="user_note", primary_category="user_note", created_at. Confirm the new collection count.
  - export: save the last card as Markdown in cards/
  - stats: total count, counts per primary_category and source_type
  - quit

  Discovery Card for a query (retrieve the top 15):
  1. Original problem (verbatim).
  2. Match labels instead of any confidence %: strong (<0.60), moderate (0.60-0.70), weak (>0.70).
     If all of the top 5 are weak, say plainly that the corpus has no strong match.
  3. Candidate terminology: 1-3 word n-grams from the titles and abstracts of the non-weak top 10.
     Score = number of retrieved docs containing the term x log(N / corpus document frequency).
     Exclude stopwords and words from the query. A term must appear in at least 2 retrieved docs.
     Show the top 5-6 terms, each with the paper_ids it came from. Label the section "Candidate terminology (extracted from retrieved sources, approximate)".
  4. Discipline map: group the results by primary_category, using a readable name map
     (nlin.AO -> Adaptation & Self-Organizing Systems, cs.HC -> Human-Computer Interaction, etc.; fall back to the raw code).
     Show the count and the best paper per group.
  5. Potential connection: the best-ranked non-weak result whose primary_category differs from the top result's.
     Label it "possible analogy, exploratory - not evidence that the mechanism transfers". If there is none, say so.
  6. Sources: top 5 with title, category, arxiv link, distance label, and one excerpt sentence
     (the abstract sentence containing the most candidate terms). User notes are shown with a [your note] tag, never presented as papers.
  7. Next step (editable hypothesis): a template sentence combining the user's problem with the top term and the connection field,
     clearly marked as a hypothesis to test, not an answer.

  Verify and report actual outputs:
  a) search with query A ("My stars move like they are following the same invisible clock; how could they behave more naturally as a group?") and show the full card
  b) add a test note with distinctive meaning but uncommon wording, search for it with a paraphrased query in the same session, and show its rank
  c) exit, restart the CLI, search again, and confirm the note is still found and the count is unchanged
  d) then delete only the test note and confirm the count is back to 399
  Put cards/ in .gitignore. Stop after this.



  Final round before submission. Do these and report the actual outputs:

  1. Card fix: add a "Your notes" section listing any user_note in the top 15, with its rank and distance label, even if it is outside the top 5 sources.
  2. Term fix: drop a candidate term if it is a substring of an already-selected longer term.
  3. Case 2 evidence: for queries C and D from eval_queries.py, print the exact query text,
     and for each of the top 3 results print: rank, distance, title, primary_category, the shared non-stopword tokens, and the most relevant abstract sentence.
     Do the same for query A's top 5. I will pick the zero-overlap examples myself.
  4. Git: git init if needed. Make sure .gitignore excludes .venv/, data/, cards/, and caches.
     Show me git status and the list of files that would be committed. Don't push.
  5. README.md draft: write ONLY these sections: Setup (py -3.13 venv, pip install), First-run downloads (the MiniLM model ~79MB to ~/.cache/chroma),
     Rebuilding the corpus (fetch_arxiv.py -> ingest.py, with expected counts and the 38% truncation note), Running the CLI (commands with an example),
     Vector DB & embedding model, and Limitations.
     Leave these four sections as headings with "TODO (written by student)": What it does; Dataset (source/unit/count/metadata); Add & search workflow; Semantic search tests.
  6. prompt_log.md: extract my prompts to you from this Claude Code session's transcript VERBATIM, in chronological order, with timestamps if available,
     plus a one-line summary of what each run produced and any debugging. Don't paraphrase my prompts.
     Stop after this.