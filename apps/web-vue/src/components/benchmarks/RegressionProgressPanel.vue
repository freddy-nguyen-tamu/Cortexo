<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  getLatestRegressionReport,
  getRegressionHistory,
} from "../../api/client";
import type {
  RegressionReport,
  RegressionReportSummary,
} from "../../types";

const latest = ref<RegressionReport | null>(null);
const history = ref<RegressionReportSummary[]>([]);
const loading = ref(true);
const refreshing = ref(false);
const errorMessage = ref("");

const summary = computed(() => latest.value?.summary);

const orderedHistory = computed<RegressionReportSummary[]>(() => {
  return [...history.value].sort((a, b) =>
    String(b.generatedAt ?? "").localeCompare(String(a.generatedAt ?? "")),
  );
});

const delta = computed(() => latest.value?.delta ?? null);

function passFail(passed?: boolean): string {
  return passed ? "PASS" : "FAIL";
}

function passFailPill(passed?: boolean): string {
  return passed ? "status-pass" : "status-fail";
}

function matchedPill(matched: boolean): string {
  return matched ? "status-pass" : "status-fail";
}

function matchedLabel(matched: boolean): string {
  return matched ? "MATCH" : "MISMATCH";
}

function scoreLabel(score?: number): string {
  return score == null ? "n/a" : String(Math.round(score * 1000) / 1000);
}

function truncatedSha(sha: string | null | undefined): string {
  if (!sha) return "n/a";
  return sha.slice(0, 12);
}

function isCurrentRun(summaryRow: RegressionReportSummary): boolean {
  return Boolean(
    latest.value?.generatedAt &&
      summaryRow.generatedAt === latest.value!.generatedAt,
  );
}

function casesByCategory(): Array<{ category: string; passed: number; total: number }> {
  const bucket = summary.value?.deterministic?.byCategory ?? {};
  return Object.entries(bucket).map(([category, values]) => ({
    category,
    passed: values.passed,
    total: values.total,
  }));
}

async function refresh() {
  refreshing.value = true;
  errorMessage.value = "";
  try {
    const [nextLatest, nextHistory] = await Promise.all([
      getLatestRegressionReport(),
      getRegressionHistory(20),
    ]);
    if (nextLatest && nextLatest.available === false) {
      latest.value = null;
    } else {
      latest.value = nextLatest;
    }
    history.value = nextHistory?.reports ?? [];
  } catch (e) {
    errorMessage.value = `Could not load regression report: ${errorText(e)}`;
  } finally {
    refreshing.value = false;
  }
}

onMounted(async () => {
  loading.value = true;
  await refresh();
  loading.value = false;
});

function errorText(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}

function changedCases(): Array<{
  caseId: string;
  previousMatched: boolean;
  currentMatched: boolean;
}> {
  return delta.value?.changedCases ?? [];
}
</script>

<template>
  <section class="panel">
    <div class="panel-header">
      <h3>Deterministic Regression</h3>
      <p class="muted">
        Committed good/bad fixtures are re-run through the executable grader. A
        regression is a mismatch between expected and actual classification —
        never a semantically-empty pass.
      </p>
    </div>

    <p v-if="loading" class="muted">Loading regression report…</p>

    <p v-if="errorMessage" class="error-message" role="alert">
      {{ errorMessage }}
    </p>

    <div v-if="!loading && !errorMessage && !latest" class="status-row">
      <span class="status-pill status-fail">EMPTY</span>
      <span class="muted">
        No regression report yet. Run make regression in the repository root
        to produce the latest report.
      </span>
    </div>

    <div v-if="latest" class="button-row">
      <button
        type="button"
        class="primary-button"
        :disabled="refreshing"
        @click="refresh"
      >
        {{ refreshing ? "Refreshing…" : "Refresh" }}
      </button>
    </div>

    <template v-if="latest">
      <div class="metric-grid">
        <div class="metric-card">
          <span class="muted">Overall</span>
          <span class="status-pill" :class="passFailPill(summary?.passedGate)">
            {{ passFail(summary?.passedGate) }}
          </span>
        </div>
        <div class="metric-card">
          <span class="muted">Suite</span>
          <div>{{ latest.suiteVersion ?? "n/a" }}</div>
        </div>
        <div class="metric-card">
          <span class="muted">Commit</span>
          <div :title="latest.git?.shortCommit ?? ''">
            {{ latest.git?.shortCommit ?? "n/a" }}
          </div>
        </div>
        <div class="metric-card">
          <span class="muted">Score</span>
          <div>
            {{
              summary && summary.overall.total > 0
                ? `${summary.overall.passed} / ${summary.overall.total}`
                : "n/a"
            }}
          </div>
        </div>
        <div class="metric-card">
          <span class="muted">Baseline hash</span>
          <div :title="latest.baselineSha256 ?? ''">
            {{ truncatedSha(latest.baselineSha256) }}
          </div>
        </div>
        <div class="metric-card">
          <span class="muted">Generated</span>
          <div>{{ latest.generatedAt ?? "n/a" }}</div>
        </div>
      </div>

      <div v-if="delta" class="metric-grid">
        <div class="metric-card">
          <span class="muted">Since previous run</span>
          <div>
            {{
              scoreLabel(delta.previousOverallScore)
            }}
            → {{ scoreLabel(delta.currentOverallScore) }}
          </div>
        </div>
        <div class="metric-card">
          <span class="muted">Score delta</span>
          <div>{{ scoreLabel(delta.scoreDelta) }}</div>
        </div>
        <div class="metric-card">
          <span class="muted">Changed cases</span>
          <div>{{ (delta.changedCases ?? []).length }}</div>
        </div>
      </div>

      <div v-if="casesByCategory().length" class="metric-grid">
        <div
          v-for="bucket in casesByCategory()"
          :key="bucket.category"
          class="metric-card"
        >
          <span class="muted">{{ bucket.category }}</span>
          <div>{{ bucket.passed }} / {{ bucket.total }}</div>
        </div>
      </div>

      <div v-if="latest.cases && latest.cases.length" class="data-table-wrap">
        <h4>Cases</h4>
        <table class="data-table">
          <thead>
            <tr>
              <th>case_id</th>
              <th>category</th>
              <th>expected</th>
              <th>actual</th>
              <th>matched</th>
              <th>duration</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="entry in latest.cases"
              :key="entry.case_id"
              :title="entry.message"
            >
              <td>{{ entry.case_id }}</td>
              <td>{{ entry.category }}</td>
              <td>
                <span class="status-pill" :class="passFailPill(entry.expected_passed)">
                  {{ passFail(entry.expected_passed) }}
                </span>
                {{ entry.expected_status }}
              </td>
              <td>
                <span class="status-pill" :class="passFailPill(entry.actual_passed)">
                  {{ passFail(entry.actual_passed) }}
                </span>
                {{ entry.actual_status }}
              </td>
              <td>
                <span class="status-pill" :class="matchedPill(entry.matched)">
                  {{ matchedLabel(entry.matched) }}
                </span>
              </td>
              <td>{{ entry.duration_ms }} ms</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h4 v-if="latest.checks && latest.checks.length">Software checks</h4>
      <div v-if="latest.checks && latest.checks.length" class="data-table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>check</th>
              <th>category</th>
              <th>result</th>
              <th>exit</th>
              <th>duration</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="check in latest.checks"
              :key="check.check_id"
            >
              <td>{{ check.check_id }}</td>
              <td>{{ check.category }}</td>
              <td>
                <span class="status-pill" :class="passFailPill(check.passed)">
                  {{ passFail(check.passed) }}
                </span>
              </td>
              <td>{{ check.return_code == null ? "n/a" : check.return_code }}</td>
              <td>{{ check.duration_ms }} ms</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="changedCases().length" class="data-table-wrap">
        <h4>Changed cases since previous run</h4>
        <table class="data-table">
          <thead>
            <tr>
              <th>case_id</th>
              <th>previous</th>
              <th>current</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="change in changedCases()"
              :key="change.caseId"
            >
              <td>{{ change.caseId }}</td>
              <td>
                <span class="status-pill" :class="passFailPill(change.previousMatched)">
                  {{ passFail(change.previousMatched) }}
                </span>
              </td>
              <td>
                <span class="status-pill" :class="passFailPill(change.currentMatched)">
                  {{ passFail(change.currentMatched) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="orderedHistory.length" class="data-table-wrap">
        <h4>History</h4>
        <table class="data-table">
          <thead>
            <tr>
              <th>generated</th>
              <th>commit</th>
              <th>deterministic</th>
              <th>cases</th>
              <th>overall</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in orderedHistory"
              :key="row.generatedAt ?? row.git?.shortCommit ?? ''"
              :class="{ 'data-row-current': isCurrentRun(row) }"
            >
              <td>{{ row.generatedAt ?? "n/a" }}</td>
              <td>{{ row.git?.shortCommit ?? "n/a" }}</td>
              <td>
                {{
                  row.summary ? scoreLabel(row.summary.deterministic.score) : "n/a"
                }}
              </td>
              <td>
                {{
                  row.summary
                    ? `${row.summary.deterministic.passed} / ${row.summary.deterministic.total}`
                    : "n/a"
                }}
              </td>
              <td>
                <span class="status-pill" :class="passFailPill(row.summary?.passedGate)">
                  {{ passFail(row.summary?.passedGate) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>