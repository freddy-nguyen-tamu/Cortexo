from pathlib import Path

from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.pre_tokenizers import ByteLevel
from tokenizers.trainers import BpeTrainer

SPECIAL_TOKENS = [
    "<pad>",
    "<bos>",
    "<eos>",
    "<unk>",
    "<fim_prefix>",
    "<fim_middle>",
    "<fim_suffix>",
]


def build_bpe_tokenizer(
    corpus_files: list[str],
    vocab_size: int = 16384,
    min_frequency: int = 2,
    special_tokens: list[str] | None = None,
) -> Tokenizer:
    tokenizer = Tokenizer(BPE(unk_token="<unk>"))
    tokenizer.pre_tokenizer = ByteLevel(add_prefix_space=False)

    trainer = BpeTrainer(
        vocab_size=vocab_size,
        min_frequency=min_frequency,
        special_tokens=special_tokens or SPECIAL_TOKENS,
        show_progress=True,
    )

    tokenizer.train(files=corpus_files, trainer=trainer)
    return tokenizer


def save_tokenizer(tokenizer: Tokenizer, path: str | Path) -> Path:
    path = Path(path)
    path = path if path.suffix else path / "tokenizer.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tokenizer.save(str(path))
    return path


def load_tokenizer(path: str | Path) -> Tokenizer:
    return Tokenizer.from_file(str(path))