"""Preview a handful of real arXiv records to inspect their metadata shape.

Makes a single request to the public arXiv API (Atom feed) and prints the
fields we expect to use later. Nothing is written to disk or to ChromaDB.

arXiv API terms ask for no more than one request every 3 seconds; this script
makes exactly one request per run.

Usage:
    python preview_arxiv.py
    python preview_arxiv.py --query 'all:"collective behavior"' --max-results 3
"""

import argparse
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

API_URL = "https://export.arxiv.org/api/query"
DEFAULT_QUERY = 'all:"swarm intelligence"'
MAX_ALLOWED_RESULTS = 10  # this phase is for inspection, not ingestion
TIMEOUT_SECONDS = 20
USER_AGENT = "ProblemSolvingLab/0.1 (metadata preview; educational project)"

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}


def fetch_feed(query: str, max_results: int) -> bytes:
    params = urllib.parse.urlencode({
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    })
    request = urllib.request.Request(f"{API_URL}?{params}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


def clean(text: str | None) -> str:
    """Collapse the line breaks and indentation arXiv puts inside titles/abstracts."""
    return " ".join((text or "").split())


def parse_entry(entry: ET.Element) -> dict:
    abs_url = clean(entry.findtext("atom:id", namespaces=NS))
    primary = entry.find("arxiv:primary_category", NS)
    primary_term = primary.get("term") if primary is not None else None
    all_terms = [c.get("term") for c in entry.findall("atom:category", NS)]
    abstract = clean(entry.findtext("atom:summary", namespaces=NS))
    return {
        "id": abs_url.rsplit("/abs/", 1)[-1],
        "title": clean(entry.findtext("atom:title", namespaces=NS)),
        "abstract": abstract,
        "primary_category": primary_term,
        "other_categories": [t for t in all_terms if t != primary_term],
        "url": abs_url,
        "published": clean(entry.findtext("atom:published", namespaces=NS)),
        "abstract_chars": len(abstract),
        "abstract_words": len(abstract.split()),
    }


def print_paper(index: int, paper: dict) -> None:
    print(f"\n[{index}] {paper['title']}")
    print(f"    id:               {paper['id']}")
    print(f"    primary category: {paper['primary_category']}")
    print(f"    other categories: {', '.join(paper['other_categories']) or '(none)'}")
    print(f"    published:        {paper['published']}")
    print(f"    url:              {paper['url']}")
    print(f"    abstract length:  {paper['abstract_chars']} chars, ~{paper['abstract_words']} words")
    print(textwrap.indent(textwrap.fill(paper["abstract"], width=96), "    | "))


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview arXiv paper metadata.")
    parser.add_argument("--query", default=DEFAULT_QUERY,
                        help=f"arXiv search_query syntax (default: {DEFAULT_QUERY})")
    parser.add_argument("--max-results", type=int, default=5,
                        help=f"number of records, 1-{MAX_ALLOWED_RESULTS} (default: 5)")
    args = parser.parse_args()
    max_results = max(1, min(args.max_results, MAX_ALLOWED_RESULTS))

    print(f"Querying arXiv: {args.query!r} (max {max_results} results)")
    try:
        raw = fetch_feed(args.query, max_results)
    except urllib.error.HTTPError as e:
        print(f"ERROR: arXiv API returned HTTP {e.code} {e.reason}. No data retrieved.", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"ERROR: could not reach arXiv API ({e}). No data retrieved.", file=sys.stderr)
        return 1

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"ERROR: response was not valid Atom XML ({e}).", file=sys.stderr)
        return 1

    total = root.findtext("opensearch:totalResults", namespaces=NS)
    entries = root.findall("atom:entry", NS)
    # arXiv reports query errors as a single entry whose id points at /api/errors.
    if len(entries) == 1 and "/api/errors" in (entries[0].findtext("atom:id", namespaces=NS) or ""):
        print(f"ERROR: arXiv rejected the query: {clean(entries[0].findtext('atom:summary', namespaces=NS))}",
              file=sys.stderr)
        return 1

    print(f"Total matches reported by arXiv: {total}; retrieved: {len(entries)}")
    if not entries:
        print("No papers returned for this query.")
        return 0

    papers = [parse_entry(e) for e in entries]
    for i, paper in enumerate(papers, start=1):
        print_paper(i, paper)

    word_counts = [p["abstract_words"] for p in papers]
    print(f"\nAbstract word counts: min={min(word_counts)}, max={max(word_counts)}, "
          f"mean={sum(word_counts) / len(word_counts):.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
