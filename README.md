# Study Assistant (Slide Finder)

I built this for my Netcentric Architecture course. You type a topic or a question, in English or Thai, and it tells you which chapter and pages of the course slides to read. The web page does all the work in your browser, so it needs no server and no API key. The same search also runs from the command line and as a small REST API, and on my own computer Claude can use it to explain a topic straight from the slides.

Live demo: https://pbetp.github.io/study-assistant/ (the first visit downloads a search model of about 135 MB, and the page shows only slide titles and page numbers).

```
> udp
Start reading: Chapter 3, p.24-29
  UDP: User Datagram Protocol · UDP: Transport Layer Actions
Also related:
  Chapter 3, p.137      QUIC: Quick UDP Internet Connections

> NAT ทำงานอย่างไร
Start reading: Chapter 4, p.64-68
  NAT: network address translation

> pizza
Not found in the slides.
```

The course slides are copyrighted, so they are not in this repository. Put your own PDFs in `data/`, which git ignores. The index in `site/index/` holds only slide titles, page numbers and vectors, never the slide text.

## Using it

### Web page

Open the [live demo](https://pbetp.github.io/study-assistant/) on a phone or a computer. The first visit downloads the search model (about 135 MB) and the browser keeps it, so later visits are quick. A link such as `...?q=udp` runs that search as soon as the page opens.

### Command line (Windows, PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 1. put your PDFs in data\
# 2. build the index once (the first run downloads the model into .cache\)
.\.venv\Scripts\python.exe -m app.cli index

# 3. search
.\.venv\Scripts\python.exe -m app.cli find udp     # one search
.\.venv\Scripts\python.exe -m app.cli find         # keep asking: the model loads once
```

### REST API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api:create_default_app --factory
```

Then open `http://127.0.0.1:8000/find?q=udp`, or `http://127.0.0.1:8000/docs` for a page where you can try queries.

### Asking Claude (local RAG over MCP)

`mcp_server.py` gives Claude one tool, `find_slides`. When you ask Claude about the course, it calls the tool. The tool runs the same search, reads the text of the matching pages from the PDFs in `data/`, and hands that text to Claude, which explains the topic and says which chapter and pages it used.

```powershell
claude mcp add study-assistant -- C:\path\to\study-assistant\.venv\Scripts\python.exe C:\path\to\study-assistant\mcp_server.py
```

Then ask something like "Explain UDP from my course slides". The first question takes about 10 seconds while the model loads.

This only works on your own computer. The slide text comes from your local PDFs and is never uploaded, and the search model needs about 510 MB of memory (I measured it), more than a free cloud server gives you. If a chapter's PDF is missing from `data/`, Claude still gets the chapter and page numbers.

## Publishing the web page

The page is plain files in `site/`, so GitHub Pages can host it for free.

1. Build the index from your slides, then commit it (`app.cli index` writes `site\index\`):
   ```powershell
   git add site\index; git commit -m "Update slide index"; git push
   ```
2. In the repository, set Settings > Pages > Source to GitHub Actions. The workflow in `.github/workflows/pages.yml` then publishes `site/` on every push that changes it.

Anyone with the link can open the page and read the slide titles. If the slides are not yours to share, keep the repository and the page private, or leave `site/index/` unpublished.

## How it works

```
index (once, on your PC)
  PDF ──▶ one Page per slide ──▶ vector ──▶ site/index/  vectors.bin  pages.json  config.json
          chapter, number, title  (ONNX model)            └──── read by Python AND by the web page

search (the same steps in Python and in the browser)
  query ──▶ vector ──▶ compare with every page vector ──▶ 15 closest pages
        ──▶ drop pages below MIN_SCORE
        ──▶ merge neighbouring pages into ranges  (p.43, 44, 45, 46 → p.43-46)
        ──▶ best range + other ranges whose title shares a word with the query

ask Claude (MCP, on your PC)
  question ──▶ Claude calls find_slides ──▶ search (above) ──▶ text of those pages from data/*.pdf
           ──▶ Claude explains from that text and names the chapter and pages
```

## What each file is for

| File | Job |
|---|---|
| `site/index.html` | The web page: layout and colours |
| `site/app.js` | What the page does: loads the index and the model, shows results |
| `site/search.js` | The search logic in JavaScript (a port of `app/search.py`) |
| `site/search.test.mjs` | Tests for `search.js` |
| `site/index/` | The search index: `vectors.bin`, `pages.json`, `config.json` |
| `app/ingest.py` | Reads the PDFs: chapter, page number, title and text of every slide |
| `app/embed.py` | Turns text into a vector with the ONNX model (and a fake one for tests) |
| `app/index.py` | The index: saves it to and loads it from 3 files, and searches it |
| `app/search.py` | The finder: closest pages, merged into ranges, then the results |
| `app/config.py` | Folder locations and the tuned search values |
| `app/cli.py` | Command line |
| `app/api.py` | REST API |
| `mcp_server.py` | MCP server: lets Claude search the slides and read the matching pages |
| `eval/questions.json` | The 65 evaluation queries with their expected pages |
| `eval/run_eval.py` | Scores the finder on those queries |
| `tests/` | Offline tests, one file per module (`conftest.py` holds the shared test data) |
| `requirements.txt` | The Python packages to install |
| `pyproject.toml` | Settings for the linter (ruff) and the test runner (pytest) |
| `.github/workflows/ci.yml` | Runs lint and all tests on every push |
| `.github/workflows/pages.yml` | Publishes `site/` to GitHub Pages |
| `.gitignore` | Keeps the PDFs, the downloaded model and `.venv` out of git |
| `app/__init__.py`, `eval/__init__.py` | Empty files that mark the folders as Python packages |

## Design choices

I measured before deciding on each of these.

- I don't use a vector database. There are only 625 vectors (1 MB), and comparing a query with all of them and sorting takes 0.03 ms. Even 100,000 vectors would take 8 ms, so the index is a plain matrix in a file. A database such as Chroma starts to matter at hundreds of thousands of vectors. An earlier version did use Chroma, and taking it out removed 52 packages (217 MB) and let Python and the web page share one index.
- A whole page is the unit of search. Slides are short, about 450 characters on average. An earlier version split them into chunks of 250 to 2000 characters, and the smaller chunks never helped.
- A slide's title is the text in its largest font. The first line is often a label inside a diagram. Taking the largest text gave a sensible title on 620 of the 625 pages, which I checked by reading the whole list. The other 5 are diagram-only slides and show as "(diagram slide, no title)".
- Neighbouring pages are merged into ranges, because a topic usually spans several slides and a range is one place to start reading.
- Pages with fewer than 8 words are skipped. Dividers such as "Additional Chapter 5 slides" are almost empty, so they used to match random queries like "pizza".
- An extra "also related" range only appears if its title shares a word with the query. Without that rule most extra lines were unrelated pages that happened to score almost as high.
- Python and the browser use the same model. The quantized ONNX version of multilingual-e5-small (118 MB) finds the same pages as the full PyTorch model and runs in a browser through transformers.js, which also let me drop PyTorch from the project.
- The JavaScript finder is checked against the Python one. Given the same query vectors, both return identical results on all 65 evaluation queries, and `node --test` runs unit tests of `search.js` in CI.
- The web page, the command line and the API don't use an LLM. An earlier version had a local LLM write answers, but for "where do I start reading?" a list of pages is faster and can't invent anything. Explanations come from Claude through the MCP server, which gives Claude the real slide text to work from.

## Evaluation

`eval/questions.json` has 65 queries, each with the chapter and pages that answer it. There are 35 short topics like the ones you would type (5 of them in Thai), 20 full questions, and 10 off-topic queries that only count as correct if the finder says "not found". A query is a hit at k when an expected page falls inside one of the first k results. The finder shows up to 3 results, so hit@3 means the right page is on the screen.

Python (`python -m eval.run_eval`, using the index you built):

| queries | n | hit@1 | hit@3 |
|---|---|---|---|
| topic | 35 | 89% | 94% |
| question | 20 | 70% | 75% |
| off-topic | 10 | 70% | 70% |
| all | 65 | 80% | 85% |

I also ran the same 65 queries through the real web page in desktop Chrome, driven by a script, and got identical results: 80% hit@1 and 85% hit@3 overall.

Two things to keep in mind when reading these numbers. Short key terms work best, because the extra words in a long question pull in other slides. And the numbers are optimistic: I wrote the queries myself from the slide titles rather than taking them from official exercises, and I tuned `MIN_SCORE` and the "also related" rule on these same queries. Each query is worth 3 percentage points for a topic, 5 for a question and 10 for an off-topic probe.

## Tests and lint

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
node --test site/search.test.mjs
```

There are 55 Python tests and 7 JavaScript tests. They build tiny PDFs on the fly and use a fake embedder, so they need no network, no model and no slides. GitHub Actions runs all three commands on every push (`.github/workflows/ci.yml`).

## Known limitations

- I tested the web page in desktop Chrome but not yet on a phone. The first visit downloads about 135 MB, and the page used roughly 800 MB of memory in Chrome, which a small phone may not have.
- The MCP server only works on a computer that has the PDFs in `data/`.
- Diagrams are images or scattered labels, so a topic that only appears inside a figure can be missed.
- Thai queries find the best range well, but "also related" lines need an English term in the query (for example "NAT" in "NAT ทำงานอย่างไร").
- `MIN_SCORE` (0.82) only roughly separates on-topic from off-topic queries: 3 of the 10 off-topic probes still return a page. Scores depend on the model, so measure again if you change `EMBED_MODEL` in `app/config.py`.
- The browser and Python turn text into tokens with different code, so their results can differ slightly, for example by one page at the edge of a range.
