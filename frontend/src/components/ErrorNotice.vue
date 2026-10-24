<script setup lang="ts">
import { ApiError } from "../api/client";
defineProps<{ error: unknown }>();
</script>
<template>
  <q-banner v-if="error" class="error-banner rounded-borders" role="alert">
    <template #avatar><q-icon name="error_outline" /></template>
    {{ error instanceof Error ? error.message : String(error) }}
    <template v-if="error instanceof ApiError && error.payload">
      <div class="text-caption">Referência: {{ error.payload.request_id }}</div>
      <div v-for="(detail, i) in error.payload.erro.detalhes" :key="i">
        {{ detail.campo }}: {{ detail.mensagem }}
      </div>
    </template>
    <slot />
  </q-banner>
</template>
