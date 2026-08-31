"""Evaluation: runner, pass@k, hallucination validators, resource metrics, calibration."""

from cortexo_ml.evaluation.runner import run_evaluation, RunOutcome
from cortexo_ml.evaluation.pass_at_k import compute_pass_at_k, pass_at_k_batch
from cortexo_ml.evaluation.hallucination import RepositoryFactChecker, check_output_against_repository, HallucinationReport
from cortexo_ml.evaluation.resource_metrics import percentile, compute_resource_report, ResourceMetrics
from cortexo_ml.evaluation.calibration import calibrate, brier_score, abstain_selection

__all__ = [
    "run_evaluation",
    "RunOutcome",
    "compute_pass_at_k",
    "pass_at_k_batch",
    "RepositoryFactChecker",
    "check_output_against_repository",
    "HallucinationReport",
    "percentile",
    "compute_resource_report",
    "ResourceMetrics",
    "calibrate",
    "brier_score",
    "abstain_selection",
]