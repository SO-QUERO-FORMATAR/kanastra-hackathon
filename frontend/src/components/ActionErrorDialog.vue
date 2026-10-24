<script setup lang="ts">
import { useId } from "vue";
import { ApiError } from "../api/client";
import { errorMessage } from "../utils";
withDefaults(
  defineProps<{
    error: unknown;
    title: string;
    guidance: string;
    dismissLabel?: string;
    actionLabel?: string;
    loading?: boolean;
  }>(),
  { dismissLabel: "Entendi" },
);
const emit = defineEmits<{ close: []; action: [] }>();
const titleId = useId(),
  descriptionId = useId();
</script>
<template>
  <q-dialog
    :model-value="!!error"
    :aria-labelledby="titleId"
    :aria-describedby="descriptionId"
    @update:model-value="!$event && emit('close')"
  >
    <q-card class="feedback-dialog">
      <q-card-section>
        <q-icon
          name="error_outline"
          color="negative"
          size="32px"
          aria-hidden="true"
        />
        <h2 :id="titleId" class="q-mt-md">{{ title }}</h2>
        <div :id="descriptionId">
          <p class="q-mt-md">{{ error ? errorMessage(error) : "" }}</p>
          <p class="subtitle">{{ guidance }}</p>
        </div>
        <details
          v-if="error instanceof ApiError && error.payload"
          class="q-mt-lg"
        >
          <summary>Detalhes para suporte</summary>
          <div class="text-caption q-mt-sm">
            Referência: {{ error.payload.request_id }}
          </div>
          <div
            v-for="(detail, i) in error.payload.erro.detalhes"
            :key="i"
            class="text-caption"
          >
            {{ detail.campo }}: {{ detail.mensagem }}
          </div>
        </details>
      </q-card-section>
      <q-card-actions align="right" class="q-pa-md q-gutter-sm">
        <q-btn
          :flat="!!actionLabel"
          :outline="!actionLabel"
          color="primary"
          :label="dismissLabel"
          autofocus
          @click="emit('close')"
        />
        <q-btn
          v-if="actionLabel"
          color="primary"
          :label="actionLabel"
          :loading="loading"
          @click="emit('action')"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>
