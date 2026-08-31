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