"""Build and render a Discovery Card from retrieval hits (no LLM; heuristics in concepts.py)."""

from concepts import (STRONG_BELOW, WEAK_ABOVE, best_sentence, candidate_terms, category_name,
                      match_label)

TERM_POOL = 10   # terms come from the non-weak hits among the top 10
SOURCES_SHOWN = 5


def _abstract(hit: dict) -> str:
    """Document text minus the leading title, if the document was stored as title + blank line + body."""
    head, sep, body = hit["document"].partition("\n\n")
    return body if sep else head


def _is_note(hit: dict) -> bool:
    return hit["meta"].get("source_type") == "user_note"


def build_card(query: str, hits: list[dict], df: dict[str, int], corpus_size: int) -> dict:
    for hit in hits:
        hit["label"] = match_label(hit["distance"])

    top5_all_weak = all(h["label"] == "weak" for h in hits[:5])
    term_hits = [h for h in hits[:TERM_POOL] if h["label"] != "weak"]
    terms = candidate_terms(query, term_hits, df, corpus_size)

    groups: dict[str, list[dict]] = {}
    for hit in hits:
        groups.setdefault(hit["meta"]["primary_category"], []).append(hit)

    connection = None
    if hits:
        top_cat = hits[0]["meta"]["primary_category"]
        connection = next((h for h in hits[1:] if h["label"] != "weak" and not _is_note(h)
                           and h["meta"]["primary_category"] != top_cat), None)

    return {"query": query, "hits": hits, "top5_all_weak": top5_all_weak,
            "terms": terms, "groups": groups, "connection": connection}


def _source_line(hit: dict) -> str:
    meta = hit["meta"]
    if _is_note(hit):
        return (f"**[your note]** {meta['title']} — `{hit['id']}` (added {meta.get('created_at', '?')}) — "
                f"{hit['label']} match ({hit['distance']:.3f})")
    return (f"**{meta['title']}** — {category_name(meta['primary_category'])} (`{meta['primary_category']}`) — "
            f"{meta['source_url']} — {hit['label']} match ({hit['distance']:.3f})")


# (key, heading) in card order. Each section body is plain Markdown without its heading, so the
# CLI/export (render_markdown) and the web app (app.py) render the same text.
SECTIONS = [
    ("problem", "Your problem"),
    ("match", "Match strength"),
    ("terms", "Candidate terminology (extracted from retrieved sources, approximate)"),
    ("disciplines", "Discipline map"),
    ("connection", "Potential connection"),
    ("sources", "Sources"),
    ("notes", "Your notes"),
    ("next_step", "Next step (editable hypothesis)"),
]


def render_sections(card: dict) -> dict[str, str]:
    """Markdown body for each section key in SECTIONS."""
    hits, terms, conn = card["hits"], card["terms"], card["connection"]
    sections: dict[str, list[str]] = {}

    sections["problem"] = [f"> {card['query']}"]

    out = [f"Labels by cosine distance: strong < {STRONG_BELOW:.2f}, moderate {STRONG_BELOW:.2f}–{WEAK_ABOVE:.2f}, "
           f"weak > {WEAK_ABOVE:.2f}. These are distance bands, not confidence scores.", ""]
    counts = {lab: sum(h["label"] == lab for h in hits) for lab in ("strong", "moderate", "weak")}
    out.append(f"Top {len(hits)}: {counts['strong']} strong, {counts['moderate']} moderate, {counts['weak']} weak.")
    if card["top5_all_weak"]:
        out.append("")
        out.append("**The corpus has no strong match for this problem** — all of the top 5 results are weak. "
                   "Treat everything below with extra caution.")
    sections["match"] = out

    if terms:
        sections["terms"] = [f"- **{t['term']}** — in {len(t['paper_ids'])} sources: {', '.join(t['paper_ids'])}"
                             for t in terms]
    else:
        sections["terms"] = ["_No term appeared in at least 2 non-weak sources._"]

    sections["disciplines"] = [
        f"- **{category_name(code)}** (`{code}`) — {len(group)} result(s); best: "
        f"{group[0]['meta']['title']} ({group[0]['label']}, {group[0]['distance']:.3f})"
        for code, group in sorted(card["groups"].items(), key=lambda kv: (-len(kv[1]), kv[1][0]["distance"]))
    ]

    out = ["_Possible analogy, exploratory — not evidence that the mechanism transfers._", ""]
    if conn:
        out.append(f"{category_name(conn['meta']['primary_category'])}: **{conn['meta']['title']}** "
                   f"({conn['meta']['source_url']}, {conn['label']} match, {conn['distance']:.3f})")
    else:
        out.append("No non-weak result from a different field than the top result.")
    sections["connection"] = out

    out = []
    term_strings = [t["term"] for t in terms]
    for i, hit in enumerate(hits[:SOURCES_SHOWN], start=1):
        out.append(f"{i}. {_source_line(hit)}")
        out.append(f"   > {best_sentence(_abstract(hit), term_strings)}")
    sections["sources"] = out

    notes = [(rank, h) for rank, h in enumerate(hits, start=1) if _is_note(h)]
    if notes:
        sections["notes"] = [f"- Rank {rank} of {len(hits)}: **[your note]** {hit['meta']['title']} — "
                             f"`{hit['id']}` — {hit['label']} match ({hit['distance']:.3f})"
                             for rank, hit in notes]
    else:
        sections["notes"] = [f"_None of your notes are in the top {len(hits)}._"]

    if terms:
        field = (category_name(conn["meta"]["primary_category"]) if conn
                 else category_name(hits[0]["meta"]["primary_category"]))
        sections["next_step"] = [
            f"_Hypothesis to test, not an answer:_ The problem \"{card['query']}\" may be discussed in the "
            f"literature under the term **\"{terms[0]['term']}\"**, and work in **{field}** may offer an "
            f"analogous approach worth checking."]
    else:
        sections["next_step"] = ["_No hypothesis generated: no candidate term was found. Try rephrasing or adding notes._"]

    return {key: "\n".join(lines) for key, lines in sections.items()}


def render_markdown(card: dict) -> str:
    bodies = render_sections(card)
    out = ["# Discovery Card", ""]
    for n, (key, heading) in enumerate(SECTIONS, start=1):
        out += [f"## {n}. {heading}", "", bodies[key], ""]
    return "\n".join(out)
