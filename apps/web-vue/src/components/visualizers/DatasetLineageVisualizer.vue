<script setup lang="ts">
defineProps<{
  data?: unknown
}>();
</script>

<template>
  <section>
    <h3>Dataset Lineage Visualizer</h3>
    <pre>{{ JSON.stringify(data ?? {}, null, 2) }}</pre>
  </section>
</template>