<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { listEvaluationTasks, runEvaluation } from "../../api/client";
import type {
  EvaluationRunRecord,
  EvaluationTaskSummary,
  GraderResult,
} from "../../types";

const tasks = ref<EvaluationTaskSummary[]>([]);
const selectedTaskId = ref("");
const modelVariantId = ref("echo-demo");
const seed = ref(42);
const maxNewTokens = ref(256);
const temperature = ref(0.2);
const loadingTasks = ref(true);
const running = ref(false);
const errorMessage = ref("");
const result = ref<EvaluationRunRecord | null>(null);

const selectedTask = computed<EvaluationTaskSummary | null>(() => {
  return tasks.value.find((t) => t.taskId === selectedTaskId.value) ?? null;
});

const graderResult = computed<GraderResult | null>(() => {
  const tests = result.value?.tests;
  if (
    tests &&
    typeof tests === "object" &&
    "applicable" in tests &&
    "status" in tests
  ) {
    return tests as GraderResult;
  }
  return null;
});

const generationUsage = computed<Record<string, unknown> | null>(() => {
  const usageRaw = result.value?.generation?.usage;
  if (usageRaw && typeof usageRaw === "object") {
    return usageRaw as Record<string, unknown>;
  }
  return null;
});

onMounted(async () => {
  try {
    tasks.value = await listEvaluationTasks();
    if (tasks.value.length > 0) {
      selectedTaskId.value = tasks.value[0].taskId;
    }
  } catch (e) {
    errorMessage.value =
      "Could not load benchmark tasks. The executable grader may be disabled " +
      `on the backend (${errorText(e)}).`;
  } finally {
    loadingTasks.value = false;
  }
});

function errorText(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}

async function run() {
  const task = selectedTask.value;
  if (!task || running.value) return;
  running.value = true;
  errorMessage.value = "";
  result.value = null;
  try {
    result.value = await runEvaluation({
      taskId: task.taskId,
      modelVariantId: modelVariantId.value.trim() || "echo-demo",
      repositorySnapshotId: task.repositorySnapshotId ?? null,
      seed: seed.value,
      generation: {
        temperature: temperature.value,
        maxNewTokens: maxNewTokens.value,
        topP: 0.95,
        topK: 50,
      },
    });
  } catch (e) {
    errorMessage.value = `Evaluation request failed: ${errorText(e)}`;
  } finally {
    running.value = false;
  }
}
</script>

<template>
  <section class="panel">
    <div class="panel-header">
      <h3>Executable Evaluation Grader</h3>
      <p class="muted">
        Runs the selected task's model output through sandbox compile + hidden
        tests. Results are classifications, never fabricated pass/fail.
      </p>
    </div>

    <form class="form-grid" @submit.prevent="run">
      <div class="field">
        <label for="grader-task">Benchmark task</label>
        <select
          id="grader-task"
          v-model="selectedTaskId"
          :disabled="loadingTasks || running"
        >
          <option value="" disabled>Select a task…</option>
          <option
            v-for="task in tasks"
            :key="task.taskId"
            :value="task.taskId"
          >
            {{ task.taskId }}
          </option>
        </select>
      </div>

      <div class="field">
        <label for="grader-model">Model variant ID</label>
        <input
          id="grader-model"
          v-model="modelVariantId"
          type="text"
          autocomplete="off"
          :disabled="running"
        />
      </div>

      <div class="field">
        <label for="grader-seed">Seed</label>
        <input
          id="grader-seed"
          v-model.number="seed"
          type="number"
          step="1"
          :disabled="running"
        />
      </div>

      <div class="field">
        <label for="grader-tokens">Max new tokens</label>
        <input
          id="grader-tokens"
          v-model.number="maxNewTokens"
          type="number"
          step="1"
          min="1"
          :disabled="running"
        />
      </div>

      <div class="field">
        <label for="grader-temp">Temperature</label>
        <input
          id="grader-temp"
          v-model.number="temperature"
          type="number"
          step="0.1"
          min="0"
          max="2"
          :disabled="running"
        />
      </div>

      <div class="button-row">
        <button
          type="submit"
          class="primary-button"
          :disabled="running || loadingTasks || !selectedTask"
        >
          {{ running ? "Running evaluation…" : "Run evaluation" }}
        </button>
      </div>
    </form>

    <p v-if="loadingTasks" class="muted">Loading tasks…</p>

    <p
      v-if="errorMessage"
      class="error-message"
      role="alert"
    >
      {{ errorMessage }}
    </p>

    <section v-if="selectedTask" class="task-preview">
      <h4>Task preview</h4>
      <dl>
        <dt>taskId</dt>
        <dd>{{ selectedTask.taskId }}</dd>
        <dt>taskType</dt>
        <dd>{{ selectedTask.taskType }}</dd>
        <dt>language</dt>
        <dd>{{ selectedTask.language }}</dd>
        <dt>prompt</dt>
        <dd>{{ selectedTask.prompt }}</dd>
      </dl>
    </section>

    <section v-if="result" class="result-block">
      <h4>Result</h4>

      <div v-if="graderResult" class="status-row">
        <span class="status-pill" :class="graderResult.passed ? 'status-pass' : 'status-fail'">
          {{ graderResult.status }}
        </span>
        <span class="muted">
          grader {{ graderResult.passed ? "PASS" : "FAIL" }} — run
          {{ result.runId }} · task {{ result.taskId }}
        </span>
      </div>
      <div v-else class="status-row">
        <span class="status-pill">{{ result.status }}</span>
        <span class="muted">run {{ result.runId }}</span>
      </div>

      <div v-if="graderResult" class="metric-grid">
        <div class="metric-card">
          <span class="muted">candidate kind</span>
          <div>{{ graderResult.candidateKind ?? "n/a" }}</div>
        </div>
        <div class="metric-card">
          <span class="muted">candidate hash</span>
          <div :title="graderResult.candidateSha256 ?? ''">
            {{ (graderResult.candidateSha256 ?? "").slice(0, 12) }}
          </div>
        </div>
        <div class="metric-card">
          <span class="muted">changed files</span>
          <div>{{ graderResult.changedFiles.join(", ") || "none" }}</div>
        </div>
        <div class="metric-card">
          <span class="muted">changed lines</span>
          <div>{{ graderResult.changedLines }}</div>
        </div>
        <div class="metric-card">
          <span class="muted">grader duration</span>
          <div>{{ graderResult.durationMs }} ms</div>
        </div>
        <div v-if="generationUsage" class="metric-card">
          <span class="muted">generated tokens</span>
          <div>
            {{
              generationUsage.generatedTokens == null
                ? "unavailable"
                : String(generationUsage.generatedTokens)
            }}
          </div>
        </div>
      </div>

      <div v-if="graderResult" class="metric-grid">
        <div class="metric-card">
          <span class="muted">tests collected</span>
          <div>{{ graderResult.testSummary.collectedCount }}</div>
        </div>
        <div class="metric-card">
          <span class="muted">passed</span>
          <div>{{ graderResult.testSummary.passedCount }}</div>
        </div>
        <div class="metric-card">
          <span class="muted">failed</span>
          <div>{{ graderResult.testSummary.failedCount }}</div>
        </div>
        <div class="metric-card">
          <span class="muted">errors</span>
          <div>{{ graderResult.testSummary.errorCount }}</div>
        </div>
        <div class="metric-card">
          <span class="muted">skipped</span>
          <div>{{ graderResult.testSummary.skippedCount }}</div>
        </div>
      </div>

      <details v-if="result.output">
        <summary>Model output</summary>
        <pre class="output-block">{{ result.output }}</pre>
      </details>

      <details v-if="result.patch">
        <summary>Patch</summary>
        <pre class="output-block">{{ result.patch }}</pre>
      </details>

      <template v-if="graderResult">
        <details v-if="graderResult.compile">
          <summary>
            Compile stage —
            {{
              graderResult.compile.timedOut
                ? "TIMEOUT"
                : graderResult.compile.policyViolation
                  ? "POLICY"
                  : graderResult.compile.passed
                    ? "PASS"
                    : "FAIL"
            }}
          </summary>
          <pre class="log-block">exit: {{ graderResult.compile.exitCode }} · {{ graderResult.compile.durationMs }} ms
{{ graderResult.compile.stdout }}
{{ graderResult.compile.stderr }}</pre>
        </details>

        <details v-if="graderResult.testStage">
          <summary>
            Test stage —
            {{
              graderResult.testStage.timedOut
                ? "TIMEOUT"
                : graderResult.testStage.policyViolation
                  ? "POLICY"
                  : graderResult.testStage.passed
                    ? "PASS"
                    : "FAIL"
            }}
            · {{ graderResult.testStage.durationMs }} ms
          </summary>
          <pre class="log-block">exit: {{ graderResult.testStage.exitCode }}
{{ graderResult.testStage.stdout }}
{{ graderResult.testStage.stderr }}</pre>
        </details>
      </template>
    </section>
  </section>
</template>

<style scoped>
dl,
dt,
dd {
  margin: 0;
}

.task-preview dl {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 0.25rem 0.75rem;
}

.task-preview dt {
  color: inherit;
  opacity: 0.7;
}
</style>