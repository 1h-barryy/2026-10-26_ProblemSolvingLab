"""Problem-Solving Lab — local Streamlit interface.

A thin UI over the existing backend: retrieval.py (search, add_note, stats),
concepts.py (term frequencies) and card.py (build_card, render_sections).
No retrieval or card logic lives here.

Launch:
    .\\.venv\\Scripts\\python.exe -m streamlit run app.py
"""

import chromadb
import streamlit as st
from chromadb.errors import NotFoundError

import retrieval
from card import SECTIONS, build_card, render_sections
from concepts import document_frequencies
from lab_common import DB_DIR, PAPERS_COLLECTION, embedding_function

TOP_K = 15  # same as cli.py
EXAMPLES = {
    "Example A — group motion": "My stars move like they are following the same invisible clock; "
                                "how could they behave more naturally as a group?",
    "Example B — distraction": "Every time a notification pops up I get distracted and it takes ages to focus again.",
}
HEADINGS = dict(SECTIONS)

st.set_page_config(page_title="Problem-Solving Lab", page_icon="🔭", layout="centered")

st.markdown("""
<style>
:root { --amber: #E3A44B; --cyan: #6CC4CF; --ivory: #EDE7DA; --muted: #A9A498; }
h1.lab-title { font-family: Georgia, 'Times New Roman', serif; font-weight: 400; color: var(--ivory);
               letter-spacing: 0.01em; margin-bottom: 0.2rem; }
p.lab-subtitle { color: var(--muted); font-size: 1.05rem; margin-bottom: 1.8rem; }
div.lab-section { color: var(--amber); font-size: 0.78rem; font-weight: 600; letter-spacing: 0.12em;
                  text-transform: uppercase; margin-bottom: 0.1rem; }
div.lab-qualifier { color: var(--cyan); font-size: 0.82rem; margin-bottom: 0.6rem; }
.stMarkdown a { color: var(--cyan) !important; }
.stMarkdown blockquote { border-left: 2px solid var(--amber); color: var(--ivory); }
[data-testid="stMetricValue"] { color: var(--amber); }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def load_collection():
    """The existing 'papers' collection, or None if the database has not been built.

    Only the client/collection handle is cached; every query reads the live database,
    so newly added notes are searchable immediately.
    """
    if not (DB_DIR / "chroma.sqlite3").exists():
        return None  # don't let PersistentClient create an empty database here
    client = chromadb.PersistentClient(path=str(DB_DIR))
    try:
        return client.get_collection(PAPERS_COLLECTION, embedding_function=embedding_function())
    except NotFoundError:
        return None


def explore(collection, query: str) -> dict:
    hits = retrieval.search(collection, query, TOP_K)
    df = document_frequencies(retrieval.all_documents(collection))  # ~0.1 s; recomputed so notes count
    card = build_card(query, hits, df, collection.count())
    return {"query": query, "card": card, "sections": render_sections(card)}


def section(key: str, title: str, qualifier: str = "") -> None:
    """One Discovery Card section, rendered from card.py's Markdown in a bordered card."""
    with st.container(border=True):
        st.markdown(f'<div class="lab-section">{title}</div>', unsafe_allow_html=True)
        if qualifier:
            st.markdown(f'<div class="lab-qualifier">{qualifier}</div>', unsafe_allow_html=True)
        st.markdown(st.session_state.result["sections"][key])


def go_to(page: str) -> None:
    st.session_state.page = page


def set_query(text: str) -> None:
    st.session_state.query = text


st.session_state.setdefault("page", "Explore")
st.session_state.setdefault("query", "")
st.session_state.setdefault("result", None)
st.session_state.setdefault("just_added", None)
# Streamlit discards a widget's state while it isn't drawn; re-assigning keeps the problem text
# when the user visits Add Knowledge and comes back.
st.session_state.query = st.session_state.query

collection = load_collection()
if collection is None or collection.count() == 0:
    st.markdown('<h1 class="lab-title">Problem-Solving Lab</h1>', unsafe_allow_html=True)
    st.error(f"No research database found at `{DB_DIR}` (collection `{PAPERS_COLLECTION}`).")
    st.markdown("Build it once from the project folder, then restart this app:\n\n"
                "```powershell\n.\\.venv\\Scripts\\python.exe fetch_arxiv.py\n"
                ".\\.venv\\Scripts\\python.exe ingest.py\n```")
    st.stop()

# ---- Sidebar: navigation + live database statistics -------------------------------------------
with st.sidebar:
    st.radio("Section", ["Explore", "Add Knowledge"], key="page")
    st.divider()
    stats = retrieval.stats(collection)
    st.metric("Documents in database", stats["total"])
    for source_type, n in stats["by_source_type"].most_common():
        label = {"arxiv": "arXiv papers", "user_note": "Your notes"}.get(source_type, source_type)
        st.caption(f"{label}: **{n}**")
    st.caption("Read live from the local ChromaDB collection.")

st.markdown('<h1 class="lab-title">Problem-Solving Lab</h1>', unsafe_allow_html=True)
st.markdown('<p class="lab-subtitle">Describe a problem in your own words. '
            'Discover how different disciplines understand it.</p>', unsafe_allow_html=True)

# ---- Explore ----------------------------------------------------------------------------------
if st.session_state.page == "Explore":
    st.text_area("Your problem, in everyday language", key="query", height=110,
                 placeholder="e.g. When I come back to something after doing other things, I lose track of where I was.")
    cols = st.columns([1.2, 1.2, 1])
    for col, (label, text) in zip(cols, EXAMPLES.items()):
        col.button(label, on_click=set_query, args=(text,), width="stretch",
                   help="Fills in the box. Then press Explore Problem.")
    run = cols[2].button("Explore Problem", type="primary", width="stretch")

    if run:
        query = st.session_state.query.strip()
        if not query:
            st.warning("Type a problem first, or pick an example.")
        else:
            with st.spinner("Searching the research database…"):
                st.session_state.result = explore(collection, query)

    result = st.session_state.result
    if result is None:
        st.info("Describe a problem above and press **Explore Problem**. Results come from "
                f"{stats['total']} documents in the local database: real arXiv abstracts plus any notes you add.")
    else:
        card = result["card"]
        st.markdown("")
        section("problem", "1 · Original problem")
        match_text = result["sections"]["match"].replace("\n\n", "  \n")
        if card["top5_all_weak"]:
            st.warning(match_text)
        else:
            st.caption(match_text)
        section("terms", "2 · Candidate technical terminology", "Extracted from retrieved sources, approximate.")
        with st.container(border=True):
            st.markdown('<div class="lab-section">3 · Related academic disciplines</div>', unsafe_allow_html=True)
            st.markdown('<div class="lab-qualifier">The top 15 results grouped by arXiv primary category.</div>',
                        unsafe_allow_html=True)
            with st.expander(f"{len(card['groups'])} disciplines — show map", expanded=True):
                st.markdown(result["sections"]["disciplines"])
        section("connection", "4 · Potential cross-disciplinary connection")
        section("sources", "5 · Supporting research papers", "Top 5 results, each with its closest-matching sentence.")
        section("next_step", "6 · Next research question", "A template hypothesis for you to edit and test.")
        if any(h["meta"].get("source_type") == "user_note" for h in card["hits"]):
            section("notes", "7 · Relevant personal notes", "Your notes that appear in the top 15 results.")

# ---- Add Knowledge ----------------------------------------------------------------------------
else:
    st.subheader("Add Knowledge")
    st.markdown("Paste a note, idea or abstract. It is embedded and saved to the local database immediately, "
                "and it stays there after the app closes.")
    added = st.session_state.just_added
    if added:
        st.success(f"Saved **{added['title']}** as `{added['id']}`. "
                   f"The database now holds **{added['count']}** documents.")
        st.markdown("Try finding it again: go to **Explore** and describe the same idea *in different words*.")
        st.button("Go to Explore →", on_click=go_to, args=("Explore",), type="primary")
        st.divider()

    with st.form("add_note", clear_on_submit=True):
        title = st.text_input("Title (optional)")
        text = st.text_area("Note", height=180)
        submitted = st.form_submit_button("Save note", type="primary")
    if submitted:
        if not text.strip():
            st.warning("The note is empty — nothing was saved.")
        else:
            note_id = retrieval.add_note(collection, text, title)
            st.session_state.just_added = {"id": note_id, "title": title.strip() or "(untitled note)",
                                           "count": collection.count()}
            st.rerun()  # redraw so the sidebar count includes the new note
