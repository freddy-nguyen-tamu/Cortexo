# Cortexo free-GPU + analytics notebooks

The blueprint's free compute strategy (sections 78, Kaggle/Colab notes at the
end of the file):

- **Kaggle**: primary free GPU training environment (scratch pretrain, DAPT,
  LoRA/QLoRA, DPO, distillation, quantization). GPU auto-detect only; do not
  hard-code an accelerator (P100 retires 2026-09-15, T4x2 remains).
- **Colab Free**: secondary; checkpoint frequently, resume, never require an
  uninterrupted multi-day run.
- **Databricks Free Edition**: offline corpus/token/experiment analytics that
  export compact JSON/CSV/Parquet for MongoDB/PostgreSQL visualization. The
  public site never depends on a Databricks endpoint.

## Layout

```
notebooks/
|-- kaggle/01_pretrain_scratch.py      scratch Transformer pretraining, resumable
|-- kaggle/02_dapt_sft.py              DAPT + SFT + LoRA / QLoRA on Qwen2.5-Coder-0.5B
|-- kaggle/03_dpo.py                   DPO preference pairs from test verifiers
|-- kaggle/04_evaluate_and_upload.py   offline evaluation + registry handoff
|-- colab/01_pretrain_scratch.py       resume-safe scratch pretraining on Drive
|-- databricks/01_corpus_profile.py    files/languages/licenses/sizes/dedup
|-- databricks/02_token_stats.py       token frequency + compression metrics
|-- databricks/03_experiment_analytics.py  quality x latency x params x memory
|-- databricks/04_failure_taxonomy.py  failure kind x model x task
|-- databricks/05_scaling_analysis.py  scratch size vs val loss vs pass@k
```

## Run style

The `.py` files use `# %% [markdown]` / `# %% [code]` cells so any of
[Jupytext](https://jupytext.readthedocs.io/) (`.py:percent`), papermill, or a
normal Python runner can execute them. To convert at the CLI:

```bash
pip install jupytext
jupytext --to ipynb notebooks/kaggle/01_pretrain_scratch.py
```

## Rules

- Set `CORTEXO_GIT_REPO` before running and clone it into the session working
  dir (paths in the notebooks assume `/kaggle/working/Cortexo`,
  `/content/Cortexo`, `/dbfs/cortexo`).
- Checkpoint frequently; every long run must survive interruption.
- Never hard-code a GPU accelerator name.
- Every reported metric must come from a reproducible run with a recorded seed
  and artifact hashes.