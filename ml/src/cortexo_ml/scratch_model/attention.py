import torch
from torch import nn
from torch.nn import functional as F

from cortexo_ml.scratch_model.rope import precompute_rope, apply_rope

class CausalSelfAttention(nn.Module):
    def __init__(self, cfg):
        super().__init__()

        self.n_heads = cfg.n_heads
        self.n_kv_heads = cfg.n_kv_heads or cfg.n_heads
        self.head_dim = cfg.d_model // cfg.n_heads

        assert cfg.d_model % cfg.n_heads == 0
        assert cfg.n_heads % self.n_kv_heads == 0

        self.q_proj = nn.Linear(
            cfg.d_model,
            cfg.n_heads * self.head_dim,
            bias=cfg.use_bias,
        )
        self.k_proj = nn.Linear(
            cfg.d_model,
            self.n_kv_heads * self.head_dim,
            bias=cfg.use_bias,
        )
        self.v_proj = nn.Linear(
            cfg.d_model,
            self.n_kv_heads * self.head_dim,
            bias=cfg.use_bias,
        )
        self.o_proj = nn.Linear(
            cfg.n_heads * self.head_dim,
            cfg.d_model,
            bias=cfg.use_bias,
        )

        cos, sin = precompute_rope(
            self.head_dim,
            cfg.max_seq_len,
            cfg.rope_theta,
        )
        self.register_buffer("rope_cos", cos, persistent=False)
        self.register_buffer("rope_sin", sin, persistent=False)

        self.dropout = cfg.dropout

    def _repeat_kv(self, x):
        if self.n_kv_heads == self.n_heads:
            return x
        repeats = self.n_heads // self.n_kv_heads
        return x.repeat_interleave(repeats, dim=1)

    def forward(self, x):
        batch, time, _ = x.shape

        q = self.q_proj(x).view(
            batch, time, self.n_heads, self.head_dim
        ).transpose(1, 2)

        k = self.k_proj(x).view(
            batch, time, self.n_kv_heads, self.head_dim
        ).transpose(1, 2)

        v = self.v_proj(x).view(
            batch, time, self.n_kv_heads, self.head_dim
        ).transpose(1, 2)

        q = apply_rope(q, self.rope_cos, self.rope_sin)
        k = apply_rope(k, self.rope_cos, self.rope_sin)

        k = self._repeat_kv(k)
        v = self._repeat_kv(v)

        y = F.scaled_dot_product_attention(
            q,
            k,
            v,
            is_causal=True,
            dropout_p=self.dropout if self.training else 0.0,
        )

        y = y.transpose(1, 2).contiguous().view(
            batch, time, self.n_heads * self.head_dim
        )
        return self.o_proj(y)