"""Evaluation: runner, pass@k, hallucination validators, resource metrics,
calibration, the executable hidden-test grader, and the deterministic
engineering-regression harness."""

from cortexo_ml.evaluation.runner import run_evaluation, RunOutcome, model_visible_task
from cortexo_ml.evaluation.pass_at_k import compute_pass_at_k, pass_at_k_batch
from cortexo_ml.evaluation.hallucination import RepositoryFactChecker, check_output_against_repository, HallucinationReport
from cortexo_ml.evaluation.resource_metrics import percentile, compute_resource_report, ResourceMetrics
from cortexo_ml.evaluation.calibration import calibrate, brier_score, abstain_selection
from cortexo_ml.evaluation.grader import (
    ExecutableGrader,
    GraderResult,
    ExecutionStageResult,
    TestSummary,
    SandboxExecutor,
    parse_pytest_summary,
)
from cortexo_ml.evaluation.candidate_extraction import (
    Candidate,
    CandidateExtractionError,
    extract_candidate,
    validate_diff_targets,
    count_changed_lines,
    count_changed_lines_in_diff,
)
from cortexo_ml.evaluation.regression import (
    DEFAULT_SUITE,
    load_baseline,
    load_latest_report,
    history_summaries,
    public_regression_report,
    public_regression_summary,
    run_deterministic_cases,
)

__all__ = [
    "run_evaluation",
    "RunOutcome",
    "model_visible_task",
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
    "ExecutableGrader",
    "GraderResult",
    "ExecutionStageResult",
    "TestSummary",
    "SandboxExecutor",
    "parse_pytest_summary",
    "Candidate",
    "CandidateExtractionError",
    "extract_candidate",
    "validate_diff_targets",
    "count_changed_lines",
    "count_changed_lines_in_diff",
    "DEFAULT_SUITE",
    "load_baseline",
    "load_latest_report",
    "history_summaries",
    "public_regression_report",
    "public_regression_summary",
    "run_deterministic_cases",
]