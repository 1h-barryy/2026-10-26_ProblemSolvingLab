"""Interactive Problem-Solving Lab CLI.

Commands: search, add, export, stats, quit.

Usage:
    python cli.py
"""

import re
import sys
from datetime import datetime

from card import build_card, render_markdown
from concepts import document_frequencies
from lab_common import ROOT, utf8_stdout
import retrieval

CARDS_DIR = ROOT / "cards"
TOP_K = 15
HELP = """Commands:
  search  describe a problem in everyday language -> Discovery Card
  add     paste a note or abstract (end with a line containing only '.')
  export  save the last card as Markdown in cards/
  stats   collection counts
  quit    exit"""


def read_line(prompt: str) -> str | None:
    """input() that returns None on EOF and echoes input when stdin is piped (for readable transcripts)."""
    try:
        line = input(prompt)
    except EOFError:
        return None
    if not sys.stdin.isatty():
        print(line)
    return line


class Session:
    def __init__(self) -> None:
        self.collection = retrieval.open_collection()
        self._df: dict[str, int] | None = None   # corpus n-gram doc frequencies, rebuilt after add
        self.last_card: str | None = None
        self.last_query = ""

    def df(self) -> dict[str, int]:
        if self._df is None:
            self._df = document_frequencies(retrieval.all_documents(self.collection))
        return self._df

    def search(self) -> None:
        query = (read_line("Describe your problem: ") or "").strip()
        if not query:
            print("Empty query.")
            return
        hits = retrieval.search(self.collection, query, TOP_K)
        card = build_card(query, hits, self.df(), self.collection.count())
        self.last_card, self.last_query = render_markdown(card), query
        print()
        print(self.last_card)

    def add(self) -> None:
        title = (read_line("Title (optional, Enter to skip): ") or "").strip()
        print("Paste text; finish with a line containing only '.'")
        lines = []
        while (line := read_line("")) is not None and line.strip() != ".":
            lines.append(line)
        text = "\n".join(lines).strip()
        if not text:
            print("Nothing added (empty text).")
            return
        note_id = retrieval.add_note(self.collection, text, title)
        self._df = None
        print(f"Added {note_id}. Collection count is now {self.collection.count()}.")

    def export(self) -> None:
        if not self.last_card:
            print("No card yet — run 'search' first.")
            return
        CARDS_DIR.mkdir(exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "-", self.last_query.lower()).strip("-")[:40] or "card"
        path = CARDS_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slug}.md"
        path.write_text(self.last_card, encoding="utf-8")
        print(f"Saved {path}")

    def stats(self) -> None:
        s = retrieval.stats(self.collection)
        print(f"Total documents: {s['total']}")
        print("By source_type:")
        for key, n in s["by_source_type"].most_common():
            print(f"  {key:<20} {n}")
        print("By primary_category:")
        for key, n in s["by_category"].most_common():
            print(f"  {key:<20} {n}")


def main() -> int:
    utf8_stdout()
    session = Session()
    print(f"Problem-Solving Lab — {session.collection.count()} documents loaded.")
    print(HELP)
    commands = {"search": session.search, "add": session.add, "export": session.export,
                "stats": session.stats}
    while True:
        command = read_line("\nlab> ")
        if command is None or command.strip().lower() in {"quit", "exit", "q"}:
            print("Bye.")
            return 0
        action = commands.get(command.strip().lower())
        if action:
            action()
        elif command.strip():
            print(HELP)


if __name__ == "__main__":
    sys.exit(main())
