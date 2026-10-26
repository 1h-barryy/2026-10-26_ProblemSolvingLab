"""Transparent heuristics: candidate-term extraction, match labels, discipline names.

Term score = (number of retrieved docs containing the term) x log(N / corpus doc frequency).
"""

import math
import re

STRONG_BELOW = 0.60
WEAK_ABOVE = 0.70

STOPWORDS = set("""
a about above across after again against all almost along also although am among an and any are as at
be because been before being below between both but by can cannot could did do does doing done down
due during each either et etc few for from further get gets got had has have having he her here hers
him his how however i ie if in into is it its itself just less many may me might more most much must
my myself near no nor not now of off often on once one only onto or other others our ours out over own
per rather same several she should since so some such than that the their theirs them then there
therefore these they this those though through thus to too toward towards two under until up upon us
very via was we well were what when where whether which while who whom whose why will with within
without would yet you your yours
paper propose proposed present presented show shows shown study studies result results approach
approaches method methods based using use used new novel different various also work works well
find found investigate analysis provide provides first second three furthermore moreover recent
""".split())

TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

CATEGORY_NAMES = {
    "nlin.AO": "Adaptation & Self-Organizing Systems",
    "nlin.CD": "Chaotic Dynamics",
    "nlin.PS": "Pattern Formation & Solitons",
    "nlin.CG": "Cellular Automata & Lattice Gases",
    "cs.HC": "Human-Computer Interaction",
    "cs.MA": "Multiagent Systems",
    "cs.RO": "Robotics",
    "cs.AI": "Artificial Intelligence",
    "cs.GR": "Computer Graphics",
    "cs.CV": "Computer Vision",
    "cs.LG": "Machine Learning",
    "cs.NE": "Neural & Evolutionary Computing",
    "cs.SI": "Social & Information Networks",
    "cs.CY": "Computers & Society",
    "cs.SY": "Systems & Control",
    "eess.SY": "Systems & Control",
    "q-bio.NC": "Neurons & Cognition",
    "q-bio.PE": "Populations & Evolution",
    "q-bio.QM": "Quantitative Methods (Biology)",
    "physics.bio-ph": "Biological Physics",
    "physics.soc-ph": "Physics & Society",
    "cond-mat.stat-mech": "Statistical Mechanics",
    "cond-mat.soft": "Soft Condensed Matter",
    "math.OC": "Optimization & Control",
    "user_note": "Your notes",
}


def category_name(code: str) -> str:
    return CATEGORY_NAMES.get(code, code)


def match_label(distance: float) -> str:
    if distance < STRONG_BELOW:
        return "strong"
    if distance <= WEAK_ABOVE:
        return "moderate"
    return "weak"


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def _stem(word: str) -> str:
    # Crude plural folding so "groups" counts as the query word "group".
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def ngrams(text: str, max_n: int = 3) -> set[str]:
    """Distinct 1-3 word n-grams with no stopwords, no pure numbers, no 1-2 letter words."""
    words = tokens(text)
    ok = [w not in STOPWORDS and len(w) > 2 and not w.replace("-", "").isdigit() for w in words]
    grams = set()
    for n in range(1, max_n + 1):
        for i in range(len(words) - n + 1):
            if all(ok[i:i + n]):
                grams.add(" ".join(words[i:i + n]))
    return grams


def document_frequencies(documents: list[str]) -> dict[str, int]:
    df: dict[str, int] = {}
    for doc in documents:
        for gram in ngrams(doc):
            df[gram] = df.get(gram, 0) + 1
    return df


def candidate_terms(query: str, hits: list[dict], df: dict[str, int], corpus_size: int,
                    top: int = 6, min_docs: int = 2) -> list[dict]:
    """Score n-grams found in the given hits. Returns [{term, score, paper_ids}] best first."""
    query_stems = {_stem(w) for w in tokens(query)}
    found_in: dict[str, list[str]] = {}
    for hit in hits:
        for gram in ngrams(hit["document"]):
            if any(_stem(w) in query_stems for w in gram.split()):
                continue
            found_in.setdefault(gram, []).append(hit["id"])

    scored = []
    for gram, ids in found_in.items():
        if len(ids) < min_docs:
            continue
        score = len(ids) * math.log(corpus_size / max(df.get(gram, 1), 1))
        scored.append({"term": gram, "score": score, "paper_ids": ids})
    scored.sort(key=lambda t: (-t["score"], t["term"]))

    # Drop a term if it is contained (on word boundaries) in an already-selected longer term,
    # e.g. "motion" is dropped once "collective motion" is selected.
    kept: list[dict] = []
    for cand in scored:
        if any(f" {cand['term']} " in f" {k['term']} " for k in kept):
            continue
        kept.append(cand)
        if len(kept) >= top:
            break
    return kept


SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def best_sentence(text: str, terms: list[str]) -> str:
    """The sentence containing the most candidate terms; the first sentence on ties/no matches."""
    sentences = SENTENCE_SPLIT.split(text.strip()) or [text]
    def hits(s: str) -> int:
        padded = " " + " ".join(tokens(s)) + " "
        return sum(f" {t} " in padded for t in terms)
    return max(sentences, key=hits)  # max() keeps the first of equal scores
