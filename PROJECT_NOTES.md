# Problem-Solving Lab — Project Notes

Status: **Phase 1 (foundation)**. Working notes, not a README. Nothing here describes features that already exist beyond the two Phase 1 scripts.

## Product goal

Help someone describe a problem in everyday language and find out what that problem is called in academic and professional fields. That covers the terminology, the disciplines that study it, related ideas from other fields, and sources that support them.

```
Natural-language problem → Academic terminology → Related disciplines → Potential connections → Supporting sources
```

The goal is vocabulary discovery ("what is my problem called?"), not plain paper search.

## Proposed document structure (provisional)

Each item in the real vector database will hold **one research abstract, or an appropriately sized excerpt of one**. Full papers will not be stored as single items. If later sources are longer than an abstract, they will be split into chunks of about abstract size.

| Field | Where it lives in ChromaDB | Example / notes |
|---|---|---|
| `id` | record ID | Stable source ID, e.g. `arxiv:2301.13276`. Drop the version suffix (`v1`) so re-ingesting a revised paper updates the record instead of adding a duplicate. Chunks get `#chunk-N`. |
| `document` | document text (embedded) | Title + abstract, whitespace-normalized |
| `title` | metadata | |
| `source` | metadata | `arxiv` (other sources may come later) |
| `primary_category` | metadata | e.g. `cs.AI`, `nlin.AO`, `q-bio.PE` |
| `categories` | metadata | Other categories. Chroma metadata values are scalars (str/int/float/bool), so store this as a delimited string or use per-category boolean flags. Decide in Phase 2. |
| `published` | metadata | ISO date string, or year as int for filtering |
| `url` | metadata | Abstract page URL |
| `chunk_index` | metadata | Only needed if a record is an excerpt |

What the Phase 1 arXiv preview showed (4 records for `all:"swarm intelligence"`): abstracts ranged from 81 to 193 words, so one abstract fits comfortably in a single embedding (all-MiniLM-L6-v2 truncates input at 256 word-pieces). Many records have only a primary category and no others.

## Provisional semantic search cases

> ⚠️ **These are hypotheses, not verified retrieval results.** They list concepts we *expect* to be relevant and want to test retrieval against once real abstracts are ingested. None of them has been checked against a real corpus yet. (The Phase 1 smoke test used 12 hand-written notes, which proves nothing about real retrieval.)

### Case A: particles move too mechanically

> "The particles in my computer animation move too mechanically. I want them to move like a natural group, such as birds or fish."

Candidate concepts to test:
- Flocking / Boids (Reynolds' separation, alignment, cohesion), from computer graphics
- Collective motion / collective behavior, from biology and physics
- Self-propelled particles, the Vicsek model, active matter, from statistical physics
- Swarm intelligence / swarm robotics, from AI and robotics
- Emergence, self-organization, from complex systems
- Agent-based modeling, from computational social science
- Crowd simulation, social force model, from graphics and transportation
- Perlin / curl noise for organic-looking motion, from procedural animation

Disciplines to watch for: physics.bio-ph, nlin.AO, cs.MA, cs.GR, q-bio.PE, cs.RO.

### Case B: hard to return to a task after switching attention

> "When I get pulled away from something I'm working on, it's really hard to get back into it."

Candidate concepts to test:
- Task switching / switch cost, from cognitive psychology
- Attention residue, from organizational psychology
- Interruption and resumption lag, from HCI
- Prospective memory, from cognitive psychology
- Working memory capacity / goal maintenance, from cognitive neuroscience
- Memory for goals model (Altmann & Trafton), from cognitive science
- Flow state and its disruption, from positive psychology
- Context switching overhead, from software engineering and productivity research

Disciplines to watch for: cs.HC, q-bio.NC, cs.CY. arXiv covers psychology poorly, so this case may show that another source is needed (e.g. PsyArXiv, OpenAlex, Semantic Scholar).

## Open questions for later phases

- Which arXiv categories and queries should form the first real corpus, and how big should it be?
- Does the default embedding model separate "everyday phrasing" from "academic phrasing" well enough, or is a stronger model needed?
- Is arXiv alone enough given its weak coverage of the social sciences?
