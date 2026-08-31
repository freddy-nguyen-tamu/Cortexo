# Cortexo ML

Research plane for Cortexo:
- byte-level BPE tokenizer training
- decoder-only scratch transformer (RMSNorm, RoPE, SwiGLU, causal attention, optional MoE)
- pretraining / DAPT / SFT / PEFT / preference optimization
- repository ingestion, AST/symbol extraction, dependency graph
- BM25 / dense / hybrid / AST / graph retrieval
- sandboxed agents, routing, evaluation
- JSONL + MongoDB + PostgreSQL experiment tracking

## Quick start

```bash
cd ml
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
pip install -r requirements.txt
uvicorn cortexo_ml.api.main:app --reload --port 8000
```