from dataclasses import dataclass

@dataclass
class TransformerConfig:
    vocab_size: int = 16384
    max_seq_len: int = 1024
    n_layers: int = 8
    d_model: int = 512
    n_heads: int = 8
    n_kv_heads: int | None = None
    d_ff: int = 2048
    dropout: float = 0.0
    rope_theta: float = 10000.0
    rms_norm_eps: float = 1e-5
    tie_embeddings: bool = True
    use_bias: bool = False
    moe_num_experts: int = 0
    moe_top_k: int = 2

    @classmethod
    def from_dict(cls, data: dict) -> "TransformerConfig":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in (data or {}).items() if k in known})

    def to_dict(self) -> dict:
        known = {f.name for f in self.__dataclass_fields__.values()}
        return {k: v for k, v in self.__dict__.items() if k in known}