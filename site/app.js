// The page: loads the index and the search model, then answers queries in the browser.
// The search logic itself is in search.js.
import { findPages, pagesText } from "./search.js";

// Pinned version (never "latest"): the page must keep working when a new release comes out.
const TRANSFORMERS_URL = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1";
const MAX_TITLES = 5; // a long range has many slide titles; show the first few

const form = document.getElementById("form");
const input = document.getElementById("q");
const statusLine = document.getElementById("status");
const progressBar = document.getElementById("progress");
const results = document.getElementById("results");
const stats = document.getElementById("stats");

async function fetchOk(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`could not load ${url} (HTTP ${response.status})`);
  return response;
}

// The three index files written by `python -m app.cli index` (the CLI reads the same files).
async function loadIndex() {
  const [config, data, buffer] = await Promise.all([
    fetchOk("index/config.json").then((r) => r.json()),
    fetchOk("index/pages.json").then((r) => r.json()),
    fetchOk("index/vectors.bin").then((r) => r.arrayBuffer()),
  ]);
  const vectors = new Float32Array(buffer);
  if (vectors.length !== config.count * config.dim) throw new Error("index files do not match");
  return { config, data, vectors };
}

// Downloads the same quantized model the Python side uses (cached by the browser afterwards).
async function loadModel(config) {
  const { pipeline } = await import(TRANSFORMERS_URL); // dynamic: a failed download can be caught
  const files = new Map(); // file name -> {loaded, total}, to show one overall percentage
  const progress = (event) => {
    if (event.status !== "progress") return;
    files.set(event.file, { loaded: event.loaded, total: event.total });
    const all = [...files.values()];
    const total = all.reduce((sum, f) => sum + f.total, 0);
    const loaded = all.reduce((sum, f) => sum + f.loaded, 0);
    const percent = Math.round((100 * loaded) / total);
    statusLine.textContent = `Downloading the search model… ${percent}%`;
    progressBar.value = percent;
    progressBar.hidden = false;
  };
  return pipeline("feature-extraction", config.model, {
    dtype: config.dtype,
    progress_callback: progress,
  });
}

async function start() {
  statusLine.textContent = "Loading…";
  const index = await loadIndex();
  stats.textContent = `${index.config.count} slides · ${index.data.chapters.length} chapters · ${stats.textContent}`;
  const extractor = await loadModel(index.config);
  progressBar.hidden = true;
  statusLine.textContent = "Ready.";
  return { ...index, extractor };
}

const ready = start();
ready.catch((error) => {
  progressBar.hidden = true;
  statusLine.textContent = `Could not start: ${error.message}`;
});

// Makes one element. textContent (not innerHTML) keeps slide titles from being read as HTML.
function element(tag, className, text = "") {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

// Builds one result card. `position` (0, 1, 2) delays the animation so cards appear in turn.
function card(range, position) {
  const isBest = position === 0;
  const box = element("article", isBest ? "card best" : "card");
  box.style.setProperty("--i", position);

  const pageCount = range.lastPage - range.firstPage + 1;
  const top = element("div", "top");
  top.append(
    element("span", "label", isBest ? "Start reading" : "Also related"),
    element("span", "count", pageCount === 1 ? "1 page" : `${pageCount} pages`),
  );

  const titles = element("ul", "titles");
  const shown = range.titles.length ? range.titles.slice(0, MAX_TITLES) : ["(diagram slide, no title)"];
  for (const title of shown) titles.append(element("li", "", title));
  if (range.titles.length > MAX_TITLES) {
    titles.append(element("li", "", `+ ${range.titles.length - MAX_TITLES} more`));
  }

  box.append(top, element("h2", "where", `${range.chapter}, p.${pagesText(range)}`), titles);
  return box;
}

async function search(query) {
  results.replaceChildren();
  let app;
  try {
    app = await ready; // while the model is still loading, the status line already says so
  } catch {
    return; // the error is already shown
  }
  statusLine.textContent = "Searching…";
  const output = await app.extractor(app.config.query_prefix + query, {
    pooling: "mean",
    normalize: true,
  });
  const found = findPages({
    query,
    queryVec: output.data,
    data: app.data,
    vectors: app.vectors,
    config: app.config,
  });
  if (found.length === 0) {
    statusLine.textContent = "Not found in the slides. Try a shorter key term, like the examples above.";
    return;
  }
  statusLine.textContent = found.length === 1 ? "1 place to read" : `${found.length} places to read`;
  found.forEach((range, position) => results.append(card(range, position)));
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = input.value.trim();
  if (!query) return;
  history.replaceState(null, "", "?q=" + encodeURIComponent(query)); // shareable link
  search(query).catch((error) => {
    statusLine.textContent = `Something went wrong: ${error.message}`;
  });
});

// An example chip fills the box with its text and searches.
for (const chip of document.querySelectorAll(".chip")) {
  chip.addEventListener("click", () => {
    input.value = chip.textContent;
    form.requestSubmit();
  });
}

// A link like  index.html?q=udp  fills the box and searches as soon as the page is ready.
const fromLink = new URLSearchParams(location.search).get("q");
if (fromLink) {
  input.value = fromLink;
  form.requestSubmit();
}
