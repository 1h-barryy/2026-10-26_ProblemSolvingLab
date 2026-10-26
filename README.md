# Problem-Solving Lab

*A tool for discovering academic concepts through everyday questions.*

## 1. About the Project

I built this project because sometimes we know what problem we're facing, but don't know the right terms to search for or technical term to express it.

Problem-Solving Lab lets users describe a problem in natural language and find related research, technical terminology, and possible connections across different fields.

Instead of just searching for papers, I wanted to help users better understand what their problem might actually be called.

## 2. Dataset

I used the arXiv API to collect **399 real research papers** across several fields, including human-computer interaction, cognitive science, robotics, and collective behavior.

Each document contains a paper's title and abstract, along with its category and source information.

The papers are stored in a persistent ChromaDB collection using the `all-MiniLM-L6-v2` embedding model.

## 3. How It Works

Users can enter a question in everyday language, and the app searches for semantically related research.

The results are organized into a Discovery Card showing:

- Related technical terms
- Relevant academic fields
- Possible cross-disciplinary connections
- Research papers and their sources

Users can also add their own notes, search for them immediately, and find them again after restarting the app.

## 4. Why Semantic Search?

I wanted to test whether a vector database could connect everyday descriptions with academic language, even when they don't use the same words.

**Example 1 — Collective Motion**

Query: "My stars move like they are following the same invisible clock; how could they behave more naturally as a group?"

Result: *Intermittent Flocking and Fractal Collective Order Induced by Time-Varying Delays*

Rank 1 · Cosine distance: 0.582

**Example 2 — Task Interruptions**

Query: "Every time a notification pops up I get distracted and it takes ages to focus again."

Result: *Mitigating the Effects of Reading Interruptions by Providing Reviews and Previews*

Rank 3 · Cosine distance: 0.537

Neither matched paper shares exact non-stopword terms with its query in our evaluation. A simple exact-keyword search would miss these connections, while semantic search was able to retrieve them.

## 5. Setup and Run

The application runs locally using Python, ChromaDB, and Streamlit.

**Requirements:** Python 3.13

### Installation

Create a virtual environment and install dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Build the Database

Download the research papers from arXiv:

```powershell
.\.venv\Scripts\python.exe fetch_arxiv.py
```

Generate embeddings and store the papers in ChromaDB:

```powershell
.\.venv\Scripts\python.exe ingest.py
```

The database is stored locally in `data/chroma/`.

The initial dataset is not included in GitHub. These setup commands allow users to build their own local database. They only need to do this once unless they want to rebuild it.

### Run the Web App

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open **http://localhost:8501** in your browser.

The app has two main sections:

- **Explore:** Ask a question, discover related academic terminology, and explore research through Discovery Cards.
- **Add Knowledge:** Save personal notes and retrieve them through semantic search.

The original CLI is also available:

```powershell
.\.venv\Scripts\python.exe cli.py
```

## 6. Technical Details

- **Vector Database:** ChromaDB 1.5.9, using persistent local storage
- **Embedding Model:** all-MiniLM-L6-v2 (384 dimensions)
- **Distance Metric:** Cosine
- **Dataset:** 399 arXiv papers at the time of development
- **Frontend:** Streamlit
- **Search Results:** Candidate terminology, academic categories, related papers, and potential connections

The embedding model downloads automatically on first use. Once downloaded, it runs locally.

The current version does not use an LLM or RAG.

## 7. Limitations and Future Work

This is an early prototype with a relatively small research dataset.

Some abstracts exceed the embedding model's input limit, and terminology extraction still relies on heuristics. Cross-disciplinary connections are exploratory rather than verified solutions.

I'd like to improve this by adding better document chunking, expanding the research database, and eventually exploring AI and RAG to provide more useful explanations and connections.

## 8. AI Usage

I used ChatGPT for brainstorming and refining the project idea, Claude.ai for additional planning and prompt drafting, and Claude Code for implementation, debugging, and testing.

After completing the CLI, I also used Claude Code to develop a simple Streamlit interface.

The main development prompts are documented separately in `prompt_log.md`.