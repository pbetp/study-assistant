"""Settings and tuning values, in one place.

Folders are given from the project root (the folder that holds app/ and site/), so every
command works no matter which folder it is started from.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DOCS_DIR = ROOT / "data"  # your PDF slides (git-ignored, because they are copyrighted)
INDEX_DIR = ROOT / "site" / "index"  # the saved index; the web page reads it from here
MODEL_DIR = ROOT / ".cache" / "models"  # the embedding model is downloaded here once
EMBED_MODEL = "Xenova/multilingual-e5-small"  # Hugging Face repo with the ONNX model files

# How the finder is tuned. Each value was measured on the evaluation queries (see README).
# They are also written into the index (config.json), so the web page searches with the
# same numbers. Scores depend on the model: re-measure them if you change EMBED_MODEL.
MIN_SCORE = 0.82  # a page less similar than this is "not about the query"
CANDIDATE_PAGES = 15  # how many close pages to look at before merging them into ranges
MAX_RESULTS = 3  # the best range ("start reading here") + up to 2 more
