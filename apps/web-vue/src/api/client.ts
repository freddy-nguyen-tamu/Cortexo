import axios from "axios";
import type {
  EvaluationRunRecord,
  EvaluationRunRequest,
  EvaluationTaskSummary,
  RegressionHistory,
  RegressionReport,
} from "../types";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8080/api",
  timeout: 120000,
});

const EVALUATION_TIMEOUT = 360000;

interface ApiEnvelope<T> {
  status: string;
  data: T;
  message?: string | null;
}

async function unwrap<T>(response: { data: ApiEnvelope<T> | T }): Promise<T> {
  const body = response.data as ApiEnvelope<T> | T;
  if (
    body &&
    typeof body === "object" &&
    "status" in body &&
    "data" in body
  ) {
    return (body as ApiEnvelope<T>).data;
  }
  return body as T;
}

export async function listEvaluationTasks(): Promise<EvaluationTaskSummary[]> {
  const response = await api.get("/benchmarks/evaluations/tasks", {
    timeout: 30000,
  });
  const data = await unwrap<{ tasks: EvaluationTaskSummary[] }>(response);
  return data.tasks ?? [];
}

export async function runEvaluation(
  request: EvaluationRunRequest,
): Promise<EvaluationRunRecord> {
  const response = await api.post("/benchmarks/evaluations/run", request, {
    timeout: EVALUATION_TIMEOUT,
  });
  return unwrap<EvaluationRunRecord>(response);
}

export async function getLatestRegressionReport(): Promise<RegressionReport> {
  const response = await api.get("/benchmarks/regression/latest", {
    timeout: 15000,
  });
  return unwrap<RegressionReport>(response);
}

export async function getRegressionHistory(
  limit = 20,
): Promise<RegressionHistory> {
  const response = await api.get(
    `/benchmarks/regression/history?limit=${limit}`,
    { timeout: 15000 },
  );
  return unwrap<RegressionHistory>(response);
}