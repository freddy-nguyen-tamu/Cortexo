"""Corpus data pipeline: collect, clean, deduplicate, synthesize, split, pack."""

from cortexo_ml.data.collect import collect_directory, read_manifest, gate_entry
from cortexo_ml.data.clean import clean_corpus, clean_text, clean_file
from cortexo_ml.data.deduplicate import exact_deduplicate, near_deduplicate, deduplicate_stream
from cortexo_ml.data.synthesize import synthesize_task, synthesize_batch
from cortexo_ml.data.split import split_by_hash, split_hashes
from cortexo_ml.data.packing import pack_documents, fim_transform

__all__ = [
    "collect_directory",
    "read_manifest",
    "gate_entry",
    "clean_corpus",
    "clean_text",
    "clean_file",
    "exact_deduplicate",
    "near_deduplicate",
    "deduplicate_stream",
    "synthesize_task",
    "synthesize_batch",
    "split_by_hash",
    "split_hashes",
    "pack_documents",
    "fim_transform",
]