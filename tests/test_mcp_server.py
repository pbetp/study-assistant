"""Offline tests for mcp_server.py: a tiny PDF, the fake embedder, no model and no network."""

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from test_ingest import make_pdf

import mcp_server
from app.index import Index
from app.ingest import load_documents

SLIDES = [
    [(24, "UDP"), (12, "udp is a connectionless transport protocol with no handshake at all")],
    [(24, "UDP checksum"), (12, "the udp checksum detects bit errors inside a received segment")],
    [],  # an empty page, so the DNS page below is not a neighbour of the UDP pages
    [(24, "DNS"), (12, "dns translates domain names into ip addresses for every host")],
]


@pytest.fixture
def course(tmp_path, embedder):
    """A one-chapter course: (folder with the PDF, index built from it)."""
    make_pdf(tmp_path / "Chapter_1_(pdf)-123.pdf", SLIDES)
    pages = load_documents(tmp_path)
    return tmp_path, Index(pages, embedder.embed_documents([p.text for p in pages]))


# The fake embedder gives low scores, so these tests turn the minimum score off (0.0).


def test_answer_carries_the_text_of_every_page_in_the_best_range(course, embedder):
    docs_dir, index = course

    answer = mcp_server.slides_for("udp", embedder, index, docs_dir, min_score=0.0)

    best = answer["results"][0]
    assert (best["chapter"], best["pages"]) == ("Chapter 1", "1-2")
    assert [s["page"] for s in best["slides"]] == [1, 2]
    assert "connectionless" in best["slides"][0]["text"]
    assert "checksum" in best["slides"][1]["text"]
    assert "note" not in answer


def test_without_the_pdf_claude_still_learns_where_to_read(course, embedder, tmp_path):
    _, index = course

    answer = mcp_server.slides_for("udp", embedder, index, tmp_path / "no-pdfs", min_score=0.0)

    assert answer["results"][0]["pages"] == "1-2"
    assert answer["results"][0]["slides"] == []
    assert "PDF is not in" in answer["note"]


def test_nothing_close_enough_is_reported_as_not_found(course, embedder):
    docs_dir, index = course

    answer = mcp_server.slides_for("udp", embedder, index, docs_dir, min_score=1.1)

    assert answer["results"] == []
    assert "Not found" in answer["note"]


@pytest.mark.anyio
async def test_claude_sees_one_tool_with_a_description():
    async with create_connected_server_and_client_session(mcp_server.mcp) as session:
        tools = (await session.list_tools()).tools

    assert [t.name for t in tools] == ["find_slides"]
    assert "course slides" in tools[0].description
    assert tools[0].inputSchema["required"] == ["query"]
