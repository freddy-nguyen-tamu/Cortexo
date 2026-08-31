import tempfile
from pathlib import Path

from cortexo_ml.data.split import split_by_hash
from cortexo_ml.repository.ingest import ingest_repository
from cortexo_ml.repository.symbols import parse_file
from cortexo_ml.retrieval.context_builder import RepositoryIndex


def test_ingest_and_search():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "r"
        (root / "src").mkdir(parents=True)
        (root / "src" / "core.py").write_text(
            "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n"
        )
        result = ingest_repository("smoke-repo", root, snapshot_id="snap-1")
        assert result.stats["fileCount"] == 1
        assert result.stats["symbolCount"] >= 2

        index = RepositoryIndex.from_ingest(result)
        ctx = index.search("how do I subtract two numbers?", max_tokens=1024)
        assert ctx.chunks
        assert ctx.to_record()["chunks"]


def test_symbol_extension_mapping_python():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sample.py"
        content = "class Greeter:\n    def hello(self):\n        return 'hi'\n"
        parsed = parse_file(str(path), content)
        assert parsed.symbols
        assert {s.kind for s in parsed.symbols}


def test_split_by_hash_deterministic():
    rows = ["a", "b", "c", "d", "e"]
    first = split_by_hash(rows, train_seed="s", val_seed="v", test_seed="t")
    second = split_by_hash(rows, train_seed="s", val_seed="v", test_seed="t")
    assert first == second
    assert sum(len(s) for s in first) == len(rows)