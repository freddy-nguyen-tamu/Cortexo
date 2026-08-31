import torch
from torch import nn
from torch.nn import functional as F

from cortexo_ml.scratch_model.layers import SwiGLU


class MoEFFN(nn.Module):
    """Small mixture-of-experts feed-forward network (top-k routing).

    This is a practical miniature MoE experiment, not a distributed MoE
    implementation. It records per-call routing decisions so load balance,
    routing entropy and expert usage can be measured.
    """

    def __init__(self, cfg, balance_loss_weight: float = 0.01):
        super().__init__()
        self.num_experts = cfg.moe_num_experts
        self.top_k = min(cfg.moe_top_k, self.num_experts)
        self.balance_loss_weight = balance_loss_weight

        self.gate = nn.Linear(cfg.d_model, self.num_experts, bias=cfg.use_bias)
        self.experts = nn.ModuleList([
            SwiGLU(cfg.d_model, cfg.d_ff, bias=cfg.use_bias)
            for _ in range(self.num_experts)
        ])

    def forward(self, x):
        batch, seq, dim = x.shape
        flat = x.reshape(-1, dim)

        routing_logits = self.gate(flat)                      # [n, experts]
        routing_probs = F.softmax(routing_logits, dim=-1)
        top_probs, top_idx = torch.topk(routing_probs, self.top_k, dim=-1)

        top_probs = top_probs / (top_probs.sum(dim=-1, keepdim=True) + 1e-6)

        out = torch.zeros_like(flat)
        usage = torch.zeros(self.num_experts, device=x.device, dtype=torch.long)

        expert_flat = torch.tensor(self.num_experts, device=x.device)
        for i in range(self.num_experts):
            mask = top_idx == i
            if mask.any():
                weight = (top_probs * mask.to(top_probs.dtype)).sum(dim=-1, keepdim=True)
                out += weight * self.experts[i](flat)
                usage[i] = mask.sum().item()

        if self.training:
            load = usage.float() / max(1, batch * seq)
            load_balance_loss = self.num_experts * (
                (load * routing_probs.mean(dim=0)).sum()
            )
            loss = self.balance_loss_weight * F.mse_loss(load, routing_probs.mean(dim=0))
        else:
            loss = None

        entropy = -(routing_probs * routing_probs.clamp_min(1e-9).log()).sum(-1).mean()

        return out.reshape(batch, seq, dim), {
            "experts_per_token": self.top_k,
            "expert_usage": usage.tolist(),
            "routing_entropy": entropy.item(),
            "loss": loss.item() if loss is not None else None,
        }


def make_moe_model(cfg):
    """Build a scratch decoder with MoE FFNs directly.

    Returns a module exposing .blocks (list of blocks) with .ffn being MoEFFN.
    """
    from cortexo_ml.scratch_model.attention import CausalSelfAttention
    from cortexo_ml.scratch_model.layers import RMSNorm
    from cortexo_ml.scratch_model.rope import precompute_rope

    class MoEBlock(nn.Module):
        def __init__(self, c):
            super().__init__()
            self.attn_norm = RMSNorm(c.d_model, c.rms_norm_eps)
            self.attn = CausalSelfAttention(c)
            self.ffn_norm = RMSNorm(c.d_model, c.rms_norm_eps)
            self.ffn = MoEFFN(c)

        def forward(self, x):
            x = x + self.attn(self.attn_norm(x))
            out, route_info = self.ffn(self.ffn_norm(x))
            return x + out, route_info

    class MoECodeLM(nn.Module):
        def __init__(self, c):
            super().__init__()
            self.cfg = c
            self.token_embedding = nn.Embedding(c.vocab_size, c.d_model)
            self.blocks = nn.ModuleList([MoEBlock(c) for _ in range(c.n_layers)])
            self.final_norm = RMSNorm(c.d_model, c.rms_norm_eps)
            self.lm_head = nn.Linear(c.d_model, c.vocab_size, bias=False)
            if c.tie_embeddings:
                self.lm_head.weight = self.token_embedding.weight
            self.apply(self._init_module)

        def _init_module(self, module):
            if isinstance(module, nn.Linear):
                torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
                if module.bias is not None:
                    torch.nn.init.zeros_(module.bias)
            if isinstance(module, nn.Embedding):
                torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

        def forward(self, input_ids, labels=None):
            x = self.token_embedding(input_ids)
            routing = []
            for block in self.blocks:
                x, info = block(x)
                routing.append(info)
            x = self.final_norm(x)
            logits = self.lm_head(x)

            loss = None
            if labels is not None:
                shift_logits = logits[:, :-1, :].contiguous()
                shift_labels = labels[:, 1:].contiguous()
                loss = F.cross_entropy(
                    shift_logits.view(-1, shift_logits.size(-1)),
                    shift_labels.view(-1),
                    ignore_index=-100,
                )

            return {"logits": logits, "loss": loss, "routing": routing}

    return MoECodeLM(cfg)