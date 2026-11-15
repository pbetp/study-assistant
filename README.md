# Study-Assistant (Slide Finder)

Find where a topic is in your course slides. Type a topic or a question, in English or Thai, and get the chapter and page range to start reading. It runs entirely in the browser (no server, no API key), and also as a command line and a small REST API. On your own computer, Claude can also use it to explain a topic from the slides.

Live demo: https://pbetp.github.io/study-assistant-netcen-/ (the first visit downloads a search model of about 135 MB; the page shows only slide titles and page numbers).

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

> Course slides are copyrighted and are not in this repository. Put your own PDFs in `data/` (git-ignored). The index (`site/index/`) contains only slide titles, page numbers and vectors, never slide text.

## Use it

### Web page (phone or computer)

Open the [live demo](https://pbetp.github.io/study-assistant-netcen-/). The first visit downloads the search model (about 135 MB). The browser keeps it, so later visits are fast. A link like `...?q=udp` searches straight away.

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

Then open `http://127.0.0.1:8000/find?q=udp`, or `http://127.0.0.1:8000/docs` for a page where you can try it.

### Ask Claude (local RAG through MCP)

`mcp_server.py` gives Claude one tool, `find_slides`. When you ask Claude about the course, it calls the tool, the tool runs the same search and reads the text of the matching pages from the PDFs in `data/`, and Claude explains the topic from that text and names the chapter and pages.

```powershell
claude mcp add study-assistant -- C:\path\to\study-assistant-netcen-\.venv\Scripts\python.exe C:\path\to\study-assistant-netcen-\mcp_server.py
```

Then ask, for example, "Explain UDP from my Netcentric slides". The first question takes about 10 seconds while the model loads.

This part runs only on your own computer. The slide text comes from your local PDFs and is never uploaded to this repository, and the search model needs about 510 MB of memory (measured), which is more than a free cloud server offers. If a chapter's PDF is missing from `data/`, Claude still gets the chapter and page numbers.

## Publish the web page (free, no card)

The page is plain files in `site/`, so GitHub Pages can host it.

1. Build the index from your slides, then commit it (`app.cli index` writes `site\index\`):
   ```powershell
   git add site\index; git commit -m "Update slide index"; git push
   ```
2. In the repository: Settings > Pages > Source: GitHub Actions. The workflow `.github/workflows/pages.yml` publishes `site/` on every push that changes it.

Anyone with the link can open the page and see the slide titles. If the slides are not yours to share, keep the repository and the page private or do not publish `site/index/`.

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
| `app/__init__.py`, `eval/__init__.py` | Empty. They mark the folders as Python packages |

## Design choices

Each choice below comes from a measurement.

- There is no vector database. There are only 625 vectors (1 MB). Comparing the query with all of them and sorting takes 0.03 ms (measured; 100,000 vectors would still take 8 ms), so the index is a plain matrix saved in a file. A vector database such as Chroma would matter at hundreds of thousands of vectors. An earlier version used Chroma; removing it dropped 52 packages (217 MB) and let Python and the web page share one index.
- A whole page is the search unit. Slides are short (about 450 characters). An earlier version split them into chunks of 250-2000 characters, and smaller chunks never helped.
- The title is the text in the largest font. The first line of a slide is often a label inside a diagram. The largest text gave a sensible title on 620 of 625 pages (checked by reading the full list). The other 5 are diagram-only slides ("(diagram slide, no title)").
- Neighbouring pages are merged into ranges. A topic usually spans several slides, and one range is one place to read.
- Pages with fewer than 8 words are skipped. Dividers such as "Additional Chapter 5 slides" are almost empty, so they matched random queries like "pizza".
- An "also related" range is shown only if its title shares a word with the query. Without this rule most extra lines were unrelated pages with almost the same score.
- Python and the browser use one model. The quantized ONNX version of multilingual-e5-small (118 MB) searches as well as the full PyTorch one (same hit rates) and runs in a browser through transformers.js. Using it everywhere also removed PyTorch from the project.
- The JavaScript finder is checked against the Python one. On all 65 evaluation queries, the same query vectors give identical results in both (65 of 65), and `node --test` runs unit tests of `search.js` in CI.
- The web page, the command line and the API use no LLM. An earlier version wrote answers with a local LLM. For "where do I start reading?", a page list is faster and cannot invent content. Explaining is left to Claude through the MCP server, which hands Claude the real slide text to work from.

## Evaluation

`eval/questions.json` has 65 queries, each with the chapter and page(s) that answer it: 35 short topics (what you would type, including 5 in Thai), 20 full questions, and 10 off-topic queries that are correct only if the finder says "not found". A query is a hit at k if an expected page is inside one of the first k results. The finder shows up to 3, so hit@3 means "the right page is on the screen".

Python (`python -m eval.run_eval`, uses the index you built):

| queries | n | hit@1 | hit@3 |
|---|---|---|---|
| topic | 35 | 89% | 94% |
| question | 20 | 70% | 75% |
| off-topic | 10 | 70% | 70% |
| all | 65 | 80% | 85% |

The same 65 queries through the real web page (desktop Chrome, driven by a script) gave identical results: 80% hit@1 and 85% hit@3 overall.

How to read it:

- Type the key term. Short topics are the most reliable. Long questions are weaker because their extra words pull in other slides.
- The numbers are optimistic. The queries were written by the author of this repo from the slide titles, not taken from official exercises, and `MIN_SCORE` and the "also related" rule were tuned on these same queries. One query is worth 3 (topic), 5 (question) or 10 (off-topic) percentage points.

## Tests and lint

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
node --test site/search.test.mjs
```

There are 55 Python tests and 7 JavaScript tests. They build tiny PDFs on the fly and use a fake embedder, so they need no network, no model and no slides. GitHub Actions runs all three commands on every push (`.github/workflows/ci.yml`).

## Known limitations

- The web page was tested in desktop Chrome, not yet on a phone. The first visit needs about 135 MB of download, and the page used roughly 800 MB of memory in Chrome (measured), which a small phone may not have.
- The MCP server works only on a computer that has the PDFs in `data/`.
- Diagrams are images or scattered labels, so a topic that only appears inside a figure may be missed.
- Thai queries find the best range well. "Also related" lines need an English term in the query (for example "NAT" in "NAT ทำงานอย่างไร").
- `MIN_SCORE` (0.82) separates on-topic from off-topic queries only roughly: 3 of the 10 off-topic probes still return a page. Scores depend on the model, so re-measure it if you change `EMBED_MODEL` in `app/config.py`.
- The browser and Python compute vectors with different tokenizer code, so results can differ slightly (for example one extra page at the edge of a range).
