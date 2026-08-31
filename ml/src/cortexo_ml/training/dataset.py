import numpy as np
import torch
from torch.utils.data import Dataset


class MmapTokenDataset(Dataset):
    """Windowed view over a tokenized corpus stored as a single uint16 .npy file.

    The sequence-packing happens implicitly: tokens are concatenated in corpus
    order and each example is a fixed-length window. Labels are the shifted
    next tokens of the same window, so every position is trained causally.
    """

    def __init__(self, token_path, seq_len: int, start=0, end=None, mode="r"):
        arr = np.lib.format.open_memmap(token_path, mode=mode, dtype=np.uint16)
        lo = start if start is not None else 0
        hi = len(arr) if end is None else min(end, len(arr))
        self.arr = arr[lo:hi]
        self.seq_len = seq_len
        self.windows = max(0, (hi - lo) // seq_len)

    def __len__(self):
        return self.windows

    def __getitem__(self, idx):
        begin = idx * self.seq_len
        end = begin + self.seq_len + 1
        tokens = torch.from_numpy(self.arr[begin:end].astype(np.int64))
        return {
            "input_ids": tokens[:-1],
            "labels": tokens[1:],
        }


def build_datasets(token_path, seq_len, split_frac=0.95, start=None, end=None):
    arr = np.lib.format.open_memmap(token_path, mode="r", dtype=np.uint16)
    total = len(arr)
    lo = start if start is not None else 0
    hi = total if end is None else min(end, total)
    usable = hi - lo
    train_end = lo + int(usable * split_frac)

    train = MmapTokenDataset(token_path, seq_len, start=lo, end=train_end)
    eval = MmapTokenDataset(token_path, seq_len, start=train_end, end=hi)
    if len(eval) == 0:
        eval = train
    return train, eval