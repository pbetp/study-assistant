from app.config import DOCS_DIR, INDEX_DIR, MAX_RESULTS, MIN_SCORE, ROOT
from app.index import Index


def test_folders_do_not_depend_on_where_the_command_is_started(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # pretend the program was started from some other folder

    assert DOCS_DIR == ROOT / "data"
    assert len(Index.load(INDEX_DIR).pages) > 0  # the index shipped in site/index/ is still found


def test_tuning_values_are_sensible():
    assert 0 < MIN_SCORE < 1
    assert MAX_RESULTS >= 1
