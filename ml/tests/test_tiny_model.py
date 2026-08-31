import pytest

torch = pytest.importorskip("torch", reason="torch is optional; tiny-model smoke requires it")

from cortexo_ml.scratch_model.config import TransformerConfig
from cortexo_ml.scratch_model.model import ScratchCodeLM


@pytest.mark.tiny_model
def test_scratch_model_forward_backward():
    torch.manual_seed(0)
    cfg = TransformerConfig(
        vocab_size=256,
        max_seq_len=32,
        n_layers=2,
        d_model=64,
        n_heads=4,
        d_ff=128,
        dropout=0.0,
        tie_embeddings=True,
    )
    model = ScratchCodeLM(cfg)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

    input_ids = torch.randint(0, cfg.vocab_size, (2, 24))
    labels = torch.randint(0, cfg.vocab_size, (2, 24))

    first = None
    for _ in range(2):
        optimizer.zero_grad()
        out = model(input_ids=input_ids, labels=labels)
        loss = out["loss"]
        assert loss is not None and loss.isfinite()
        loss.backward()
        optimizer.step()
        if first is None:
            first = loss.item()
    assert loss.item() < first or loss.item() > 0
    del model