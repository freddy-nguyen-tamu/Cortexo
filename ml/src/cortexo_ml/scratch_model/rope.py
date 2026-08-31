import torch

def precompute_rope(head_dim: int, max_seq_len: int, theta: float, device=None):
    assert head_dim % 2 == 0
    inv_freq = 1.0 / (
        theta ** (
            torch.arange(0, head_dim, 2, device=device).float() / head_dim
        )
    )
    positions = torch.arange(max_seq_len, device=device).float()
    freqs = torch.outer(positions, inv_freq)
    return torch.cos(freqs), torch.sin(freqs)

def apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor):
    # x: [batch, heads, time, head_dim]
    x_even = x[..., 0::2]
    x_odd = x[..., 1::2]

    cos = cos[:x.size(-2)].unsqueeze(0).unsqueeze(0)
    sin = sin[:x.size(-2)].unsqueeze(0).unsqueeze(0)

    out_even = x_even * cos - x_odd * sin
    out_odd = x_even * sin + x_odd * cos

    return torch.stack((out_even, out_odd), dim=-1).flatten(-2)