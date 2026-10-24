<script setup lang="ts">
import { label } from "../utils";
defineProps<{ status: string }>();
</script>
<template>
  <span
    class="status-badge"
    :class="
      /^(CONCLUIDO|APROVADO|RECEBIDO)$/.test(status)
        ? 'positive'
        : /FALHOU|BARRADO|ERRO/.test(status)
          ? 'negative'
          : 'pending'
    "
  >
    <span class="status-dot" />
    {{ label(status) }}
  </span>
</template>
