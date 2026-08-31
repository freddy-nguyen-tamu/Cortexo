export interface ModelRecord {
  modelId: string;
  displayName: string;
  family: string;
  technique: string;
  parentModelId: string | null;
  tokenizerId: string;
  parameterCount: number;
  trainableParameterCount: number;
  activeParameterCount: number;
  precision: string;
  contextLength: number;
  architecture: Record<string, unknown>;
  trainingDatasetIds: string[];
  trainingRunIds: string[];
  alignmentMethod: string | null;
  quantization: string | null;
  license: string;
  artifactUri: string | null;
  artifactSha256: string | null;
  createdAt: string;
}

export interface GenerateRequest {
  requestId: string;
  modelVariantId: string;
  repositorySnapshotId?: string | null;
  taskId?: string | null;
  prompt: string;
  seed: number;
  generation: Record<string, unknown>;
}

export interface GenerateResponse {
  requestId: string;
  modelVariantId: string;
  output: string;
  structuredOutput: Record<string, unknown>;
  usage: Record<string, unknown>;
  trace: {
    retrievalIds: string[];
    toolCalls: unknown[];
    warnings: string[];
  };
}

export interface EvaluationTaskSummary {
  taskId: string;
  taskType: string;
  repositorySnapshotId?: string | null;
  prompt: string;
  language: string;
  timeoutSeconds: number;
  requiresTools?: boolean;
  dialect?: string;
}

export interface EvaluationRunRequest {
  taskId: string;
  modelVariantId: string;
  repositorySnapshotId?: string | null;
  seed: number;
  generation: Record<string, unknown>;
}

export interface ExecutionStageResult {
  attempted: boolean;
  passed: boolean;
  exitCode: number | null;
  timedOut: boolean;
  policyViolation: boolean;
  durationMs: number;
  stdout: string;
  stderr: string;
}

export interface GraderTestSummary {
  passedCount: number;
  failedCount: number;
  errorCount: number;
  skippedCount: number;
  collectedCount: number;
}

export interface GraderResult {
  applicable: boolean;
  passed: boolean;
  status: string;
  candidateKind: string | null;
  candidateSha256: string | null;
  candidateBytes: number;
  changedFiles: string[];
  changedLines: number;
  patchApplied: boolean;
  compile: ExecutionStageResult | null;
  testStage: ExecutionStageResult | null;
  testSummary: GraderTestSummary;
  durationMs: number;
}

export interface EvaluationRunRecord {
  runId: string;
  taskId: string;
  modelVariantId: string;
  repositorySnapshotId?: string | null;
  seed: number;
  status: string;
  generation: Record<string, unknown>;
  output: string;
  patch?: string | null;
  tests: GraderResult | Record<string, unknown>;
  metrics: Record<string, unknown>;
  createdAt: string;
}

export interface RegressionScoreBucket {
  passed: number;
  failed: number;
  total: number;
  score: number;
  percent: number;
}

export interface RegressionSummary {
  software: RegressionScoreBucket;
  deterministic: RegressionScoreBucket & {
    byCategory: Record<string, RegressionScoreBucket>;
  };
  overall: RegressionScoreBucket;
  requiredDeterministicScore: number;
  passedGate: boolean;
}

export interface RegressionGit {
  shortCommit?: string | null;
  branch?: string | null;
  dirty: boolean;
}

export interface RegressionCaseResult {
  case_id: string;
  category: string;
  task_id: string;
  expected_status: string;
  actual_status: string;
  expected_passed: boolean;
  actual_passed: boolean;
  matched: boolean;
  duration_ms: number;
  candidate_sha256: string | null;
  changed_files: string[];
  changed_lines: number;
  message: string;
}

export interface RegressionCheckResult {
  check_id: string;
  category: string;
  passed: boolean;
  duration_ms: number;
  return_code: number | null;
}

export interface RegressionChangedCase {
  caseId: string;
  previousMatched: boolean;
  currentMatched: boolean;
}

export interface RegressionDelta {
  previousOverallScore: number;
  currentOverallScore: number;
  scoreDelta: number;
  changedCases: RegressionChangedCase[];
}

export interface RegressionReport {
  available?: boolean;
  error?: string;
  suiteVersion?: string;
  generatedAt?: string;
  git?: RegressionGit;
  summary?: RegressionSummary;
  baselineSha256?: string;
  cases?: RegressionCaseResult[];
  checks?: RegressionCheckResult[];
  delta?: RegressionDelta | null;
}

export interface RegressionReportSummary {
  suiteVersion?: string;
  generatedAt?: string;
  git?: RegressionGit;
  summary?: RegressionSummary;
  delta?: RegressionDelta | null;
}

export interface RegressionHistory {
  available?: boolean;
  error?: string;
  reports?: RegressionReportSummary[];
  limit?: number;
}