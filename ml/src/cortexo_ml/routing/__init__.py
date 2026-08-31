"""Model routing: task features, rule router, full scoring table, cascades/ensembles."""

from cortexo_ml.routing.features import extract_features, infer_task_type, TaskFeatures
from cortexo_ml.routing.rules import CandidateModel, rule_select
from cortexo_ml.routing.router import Router, full_scoring_table
from cortexo_ml.routing.cascade import cascade, best_of_n

__all__ = [
    "extract_features",
    "infer_task_type",
    "TaskFeatures",
    "CandidateModel",
    "rule_select",
    "Router",
    "full_scoring_table",
    "cascade",
    "best_of_n",
]