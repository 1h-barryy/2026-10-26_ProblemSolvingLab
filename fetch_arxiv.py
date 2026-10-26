"""Fetch a small real arXiv corpus and write it to data/processed/arxiv_papers.jsonl.

Runs a fixed list of arXiv API queries (50 results each, 3 s apart, per the
arXiv API terms). Raw Atom responses are cached under data/raw/arxiv/ and
reused on later runs unless --refresh is given. Records are deduplicated by
arXiv ID with the version suffix removed; records with empty abstracts are
skipped. Any network or API error aborts the run without writing output.

Usage:
    python fetch_arxiv.py            # use cached responses where present
    python fetch_arxiv.py --refresh  # re-download every query
"""

import argparse
import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from lab_common import PAPERS_JSONL, RAW_DIR, clean, utf8_stdout

API_URL = "https://export.arxiv.org/api/query"
RESULTS_PER_QUERY = 50
DELAY_SECONDS = 3
TIMEOUT_SECONDS = 30
USER_AGENT = "ProblemSolvingLab/0.2 (small research corpus; educational project)"

# (cache key, arXiv search_query)
QUERIES = [
    ("nlin_ao", "cat:nlin.AO"),
    ("collective_motion_flocking", 'all:"collective motion" OR all:flocking'),
    ("ma_coordination", "cat:cs.MA AND all:coordination"),
    ("swarm_robotics", 'all:"swarm robotics"'),
    ("hc_interruption", "cat:cs.HC AND (all:interruption OR all:resumption)"),
    ("nc_working_memory", 'cat:q-bio.NC AND all:"working memory"'),
    ("gr_procedural_crowd", "cat:cs.GR AND (all:procedural OR all:crowd)"),
    ("pe_collective_behavior", 'cat:q-bio.PE AND all:"collective behavior"'),
]

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}
VERSION_SUFFIX = re.compile(r"v\d+$")


def download(query: str) -> bytes:
    params = urllib.parse.urlencode({
        "search_query": query,
        "start": 0,
        "max_results": RESULTS_PER_QUERY,
        "sortBy": "relevance",
        "sortOrder": "descending",
    })
    request = urllib.request.Request(f"{API_URL}?{params}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


def parse_feed(raw: bytes, query: str) -> tuple[int, list[dict]]:
    root = ET.fromstring(raw)
    entries = root.findall("atom:entry", NS)
    if len(entries) == 1 and "/api/errors" in (entries[0].findtext("atom:id", namespaces=NS) or ""):
        raise RuntimeError(f"arXiv rejected query {query!r}: "
                           f"{clean(entries[0].findtext('atom:summary', namespaces=NS))}")
    total = int(root.findtext("opensearch:totalResults", default="0", namespaces=NS))
    if total > 0 and not entries:
        # arXiv occasionally returns an empty page under load; don't treat that as real data.
        raise RuntimeError(f"arXiv reported {total} matches for {query!r} but returned no entries")

    papers = []
    for entry in entries:
        abs_url = clean(entry.findtext("atom:id", namespaces=NS))
        versioned_id = abs_url.rsplit("/abs/", 1)[-1]
        primary = entry.find("arxiv:primary_category", NS)
        primary_term = primary.get("term") if primary is not None else ""
        categories = [c.get("term") for c in entry.findall("atom:category", NS)]
        papers.append({
            "paper_id": VERSION_SUFFIX.sub("", versioned_id),
            "title": clean(entry.findtext("atom:title", namespaces=NS)),
            "abstract": clean(entry.findtext("atom:summary", namespaces=NS)),
            "primary_category": primary_term,
            "categories": categories,
            "published": clean(entry.findtext("atom:published", namespaces=NS)),
            "source_url": abs_url,
        })
    return total, papers


def main() -> int:
    utf8_stdout()
    parser = argparse.ArgumentParser(description="Fetch a small arXiv corpus.")
    parser.add_argument("--refresh", action="store_true", help="ignore cached responses")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    unique: dict[str, dict] = {}
    skipped_empty = 0
    made_request = False

    print(f"{'query':<55} {'arXiv total':>11} {'returned':>8} {'new unique':>10}")
    for key, query in QUERIES:
        cache_path = RAW_DIR / f"{key}.xml"
        if cache_path.exists() and not args.refresh:
            raw = cache_path.read_bytes()
            origin = "cache"
        else:
            if made_request:
                time.sleep(DELAY_SECONDS)
            try:
                raw = download(query)
            except urllib.error.HTTPError as e:
                print(f"\nERROR: HTTP {e.code} {e.reason} for query {query!r}. Aborting; nothing written.",
                      file=sys.stderr)
                return 1
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                print(f"\nERROR: network failure for query {query!r}: {e}. Aborting; nothing written.",
                      file=sys.stderr)
                return 1
            made_request = True
            origin = "api"

        try:
            total, papers = parse_feed(raw, query)
        except (ET.ParseError, RuntimeError) as e:
            print(f"\nERROR: {e}. Aborting; nothing written.", file=sys.stderr)
            return 1
        if origin == "api":
            cache_path.write_bytes(raw)  # only cache responses that parsed cleanly

        new = 0
        for paper in papers:
            if not paper["abstract"]:
                skipped_empty += 1
                continue
            if paper["paper_id"] in unique:
                unique[paper["paper_id"]]["matched_queries"].append(key)
                continue
            paper["matched_queries"] = [key]
            unique[paper["paper_id"]] = paper
            new += 1
        print(f"{query:<55} {total:>11} {len(papers):>8} {new:>10}   ({origin})")

    if not unique:
        print("ERROR: no papers collected.", file=sys.stderr)
        return 1

    PAPERS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with PAPERS_JSONL.open("w", encoding="utf-8") as f:
        for paper in unique.values():
            f.write(json.dumps(paper, ensure_ascii=False) + "\n")

    words = [len(p["abstract"].split()) for p in unique.values()]
    multi = sum(1 for p in unique.values() if len(p["matched_queries"]) > 1)
    print(f"\nTotal unique papers: {len(unique)}  (matched by >1 query: {multi}; "
          f"skipped empty abstracts: {skipped_empty})")
    print(f"Abstract words: min={min(words)} median={statistics.median(words):.0f} "
          f"mean={statistics.mean(words):.0f} max={max(words)}")
    q = statistics.quantiles(words, n=10)
    print(f"Abstract words deciles: {', '.join(f'{x:.0f}' for x in q)}")
    print(f"Wrote {PAPERS_JSONL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
