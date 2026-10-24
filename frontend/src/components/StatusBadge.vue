<script setup lang="ts">
import { statusLabel, statusTone } from "../analysisStatus";
defineProps<{ status: string }>();
</script>
<template>
  <span class="status-badge" :class="statusTone(status)">
    <span class="status-dot" />
    {{ statusLabel(status) }}
  </span>
</template>
