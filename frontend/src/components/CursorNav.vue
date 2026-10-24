<script setup lang="ts">
defineProps<{ next: string | null; depth: number; loading: boolean }>();
defineEmits(["back", "next"]);
</script>
<template>
  <div class="pagination">
    <span>Página {{ depth }}</span>
    <q-btn
      flat
      dense
      icon="chevron_left"
      aria-label="Página anterior"
      :disable="depth === 1 || loading"
      @click="$emit('back')"
    />
    <q-btn
      flat
      dense
      icon="chevron_right"
      aria-label="Próxima página"
      :disable="!next || loading"
      @click="$emit('next')"
    />
  </div>
</template>
