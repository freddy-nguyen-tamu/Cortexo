<script setup lang="ts">
defineProps<{
  data?: unknown
}>();
</script>

<template>
  <section>
    <h3>Router Visualizer</h3>
    <pre>{{ JSON.stringify(data ?? {}, null, 2) }}</pre>
  </section>
</template>