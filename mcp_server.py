"""MCP server: lets Claude explain a topic from the course slides (RAG, on this computer only).

    you ask Claude a question about the course
      -> Claude calls find_slides("udp")
      -> the same search as the web page finds the best page ranges      (retrieval)
      -> the text of those pages is read from the PDFs in data/
      -> Claude reads that text and explains it, naming chapter and pages (generation)

It runs only on your own computer, for two reasons: the PDFs are copyrighted and are never
uploaded, and the search model needs about 510 MB of memory. Add it to Claude Code with:

    claude mcp add study-assistant -- <project>\\.venv\\Scripts\\python.exe <project>\\mcp_server.py
"""

from functools import cache
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pypdf import PdfReader

from app.config import DOCS_DIR, INDEX_DIR, MIN_SCORE
from app.embed import Embedder, OnnxEmbedder
from app.index import Index
from app.ingest import chapter_name
from app.search import Result, find_pages

INSTRUCTIONS = """\
Slides of the Netcentric Architecture course (computer networking, based on Kurose & Ross).
Call find_slides when the user asks about this course, a lecture, or a networking topic they study.
- Explain from the slide text the tool returns. If the slides do not cover something, say so.
- Always name the chapter and pages, so the user can open the slides.
- Reply in the user's language (the slides are in English).
- The slides are copyrighted course material: explain them, do not paste whole slides.
"""

mcp = FastMCP("study-assistant", instructions=INSTRUCTIONS)


@cache  # runs once: the first question loads the model (about 10 seconds), later ones reuse it
def load_search() -> tuple[Embedder, Index]:
    return OnnxEmbedder(), Index.load(INDEX_DIR)


def read_slides(result: Result, docs_dir: Path) -> list[dict[str, Any]]:
    """The text of every page in the range, read from the chapter's PDF.

    The index stores no slide text (on purpose), so it is read from the PDF when needed.
    Returns [] if that chapter's PDF is not in docs_dir.
    """
    pdfs = [p for p in sorted(docs_dir.glob("*.pdf")) if chapter_name(p.name) == result.chapter]
    if not pdfs:
        return []
    pages = PdfReader(pdfs[0]).pages
    return [
        {"page": number, "text": (pages[number - 1].extract_text() or "").strip()}
        for number in range(result.first_page, result.last_page + 1)  # page numbers start at 1
    ]


def slides_for(
    query: str, embedder: Embedder, index: Index, docs_dir: Path, min_score: float = MIN_SCORE
) -> dict[str, Any]:
    """Search, then attach the slide text to every result. Tests call this with fakes."""
    results = [
        {
            "chapter": r.chapter,
            "pages": r.pages,
            "titles": r.titles,
            "slides": read_slides(r, docs_dir),
        }
        for r in find_pages(query, embedder, index, min_score)
    ]
    answer: dict[str, Any] = {"results": results}
    if not results:
        answer["note"] = "Not found in the slides. Try a shorter key term, such as 'udp'."
    elif not all(r["slides"] for r in results):
        answer["note"] = (
            f"Some slide text is missing because the PDF is not in {docs_dir}. "
            "For those results, tell the user which chapter and pages to read."
        )
    return answer


@mcp.tool()
def find_slides(query: str) -> dict[str, Any]:
    """Find the course slides about a topic and return their text, best match first.

    Args:
        query: A topic or a question in English or Thai, e.g. 'udp', 'slow start',
            'NAT ทำงานอย่างไร'. Short key terms work best.
    """
    embedder, index = load_search()
    return slides_for(query, embedder, index, DOCS_DIR)


if __name__ == "__main__":
    mcp.run()
