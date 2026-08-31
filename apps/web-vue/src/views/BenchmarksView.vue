<script setup lang="ts">
import EvaluationGraderPanel from "../components/benchmarks/EvaluationGraderPanel.vue";
import RegressionProgressPanel from "../components/benchmarks/RegressionProgressPanel.vue";
</script>

<template>
  <section>
    <h2>Benchmarks</h2>
    <p>
      Normalized evaluation analytics across micro-codegen, synthetic-bugfix,
      repo-understanding, code-review, security-review, database-reasoning,
      retrieval, agent-repair, and context-strategy suites. Pass/fail below is
      decided by executable tests in a restricted sandbox, never by string
      matching or gold-patch comparison.
    </p>

    <RegressionProgressPanel />

    <EvaluationGraderPanel />

    <section class="panel">
      <h3>Available benchmark families</h3>
      <ul>
        <li>micro-codegen</li>
        <li>synthetic-bugfix</li>
        <li>repo-understanding</li>
        <li>code-review</li>
        <li>security-review</li>
        <li>database-reasoning (PolyDB-SWE)</li>
        <li>retrieval</li>
        <li>agent-repair</li>
        <li>context-strategy</li>
      </ul>
    </section>
  </section>
</template>