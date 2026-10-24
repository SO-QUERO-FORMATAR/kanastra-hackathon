<script setup lang="ts">
import { ref, watch } from "vue";
import { api, type DTO } from "../api/client";
import { useCursor } from "../composables/useCursor";
import { money, label } from "../utils";
import StatusBadge from "./StatusBadge.vue";
import ErrorNotice from "./ErrorNotice.vue";
import CursorNav from "./CursorNav.vue";
import contract from "../../contracts/openapi.json";
const props = defineProps<{ arquivoId: string }>(),
  filter = ref("TODOS"),
  motivo = ref<DTO<"CodigoRecusa">>(),
  limit = ref(20),
  selected = ref<DTO<"ResultadoDTO">>(),
  snapshot = ref(0),
  finished = ref(false);
const { rows, loading, error, next, history, load, forward, back } = useCursor(
  async (cursor) => {
    const q: DTO<"ListarResultadosQuery"> = { cursor, limit: limit.value };
    if (filter.value === "ERRO_DADOS") q.tipo = "ERRO_DADOS";
    else if (filter.value !== "TODOS")
      q.status = filter.value as DTO<"StatusNota">;
    if (filter.value !== "ERRO_DADOS" && filter.value !== "APROVADO")
      q.motivo = motivo.value;
    const r = await api.resultados(props.arquivoId, q);
    snapshot.value = r.snapshot_ate_sequencia;
    finished.value = r.arquivo_finalizado;
    return r;
  },
);
watch(
  () => props.arquivoId,
  () => load(true),
  { immediate: true },
);
watch(filter, () => {
  motivo.value = undefined;
  load(true);
});
const columns = [
  {
    name: "documento",
    label: "Documento / sacado",
    field: "id",
    align: "left" as const,
  },
  { name: "status", label: "Decisão", field: "status", align: "left" as const },
  { name: "nominal", label: "Valor nominal", field: "id" },
  { name: "liquido", label: "Valor líquido", field: "valor_liquido" },
  {
    name: "motivos",
    label: "Motivo / diagnóstico",
    field: "motivos",
    align: "left" as const,
  },
  { name: "action", label: "", field: "id" },
];
const reasons = contract.components.schemas.CodigoRecusa.enum.map((value) => ({
  label: label(value),
  value,
}));
</script>
<template>
  <div class="surface section-space">
    <div class="surface-head">
      <div>
        <h2>Resultados da análise</h2>
        <p class="subtitle">Decisões e diagnósticos por linha de origem.</p>
      </div>
      <q-btn flat icon="refresh" label="Atualizar" @click="load(true)" />
    </div>
    <div class="filters">
      <q-select
        outlined
        dense
        v-model="filter"
        :options="[
          { label: 'Todos os resultados', value: 'TODOS' },
          { label: 'Aprovados', value: 'APROVADO' },
          { label: 'Barrados', value: 'BARRADO' },
          { label: 'Erros de dados', value: 'ERRO_DADOS' },
        ]"
        emit-value
        map-options
        label="Resultado"
      />
      <q-select
        outlined
        dense
        v-model="motivo"
        clearable
        :options="reasons"
        emit-value
        map-options
        label="Motivo de recusa"
        :disable="filter === 'ERRO_DADOS' || filter === 'APROVADO'"
        @update:model-value="load(true)"
      />
      <q-select
        outlined
        dense
        v-model="limit"
        :options="[10, 20, 50, 100]"
        label="Itens por página"
        @update:model-value="load(true)"
      />
    </div>
    <ErrorNotice :error="error">
      <q-btn flat label="Reiniciar consulta" @click="load(true)" />
    </ErrorNotice>
    <q-table
      flat
      :rows="rows"
      :columns="columns"
      row-key="id"
      :loading="loading"
      hide-bottom
      :pagination="{ rowsPerPage: 0 }"
      @request="load()"
    >
      <template #body-cell-documento="p">
        <q-td :props="p">
          <div class="table-primary">
            {{
              p.row.titulo?.nu_documento ??
              p.row.dados_originais.NU_DOCUMENTO ??
              "Não informado"
            }}
          </div>
          <div class="table-secondary">
            {{ p.row.titulo?.nome_sacado ?? p.row.dados_originais.NOME_SACADO }}
            · linha {{ p.row.linha }}
          </div>
        </q-td>
      </template>
      <template #body-cell-status="p">
        <q-td :props="p">
          <StatusBadge :status="p.row.status ?? 'ERRO_DADOS'" />
        </q-td>
      </template>
      <template #body-cell-nominal="p">
        <q-td :props="p">
          {{ p.row.titulo ? money(p.row.titulo.valor_nominal) : "—" }}
        </q-td>
      </template>
      <template #body-cell-liquido="p">
        <q-td :props="p" class="table-primary">
          {{ money(p.row.valor_liquido) }}
        </q-td>
      </template>
      <template #body-cell-motivos="p">
        <q-td :props="p">
          <span>
            {{
              p.row.motivos[0]?.mensagem ??
              p.row.erros_dados[0]?.mensagem ??
              "Elegível para aquisição"
            }}
          </span>
        </q-td>
      </template>
      <template #body-cell-action="p">
        <q-td :props="p">
          <q-btn
            flat
            round
            icon="open_in_new"
            aria-label="Detalhar resultado"
            @click="selected = p.row"
          />
        </q-td>
      </template>
    </q-table>
    <div v-if="!loading && !error && rows.length === 0" class="empty">
      Nenhum resultado disponível para estes filtros.
    </div>
    <div class="q-px-lg q-py-sm text-caption text-grey-7">
      Snapshot até a sequência {{ snapshot }} ·
      {{
        finished
          ? "Arquivo finalizado"
          : "Novos resultados podem surgir. Atualize para consultar."
      }}
    </div>
    <CursorNav
      :next="next"
      :depth="history.length"
      :loading="loading"
      @back="back"
      @next="forward"
    />
  </div>
  <q-dialog
    :model-value="!!selected"
    @update:model-value="selected = undefined"
  >
    <q-card v-if="selected" style="width: 680px; max-width: 95vw">
      <q-card-section class="row items-center">
        <h2>Detalhe do recebível</h2>
        <q-space />
        <q-btn
          flat
          round
          icon="close"
          v-close-popup
          aria-label="Fechar detalhe"
        />
      </q-card-section>
      <q-card-section>
        <StatusBadge :status="selected.status ?? 'ERRO_DADOS'" />
        <p class="q-mt-md">
          Linha {{ selected.linha }} · sequência {{ selected.sequencia }}
        </p>
        <div v-for="m in selected.motivos" :key="m.codigo" class="q-mb-md">
          <strong>{{ label(m.codigo) }}</strong>
          <p>{{ m.mensagem }}</p>
          <small>
            Observado: {{ m.valor_observado ?? "—" }} · Limite:
            {{ m.limite_aplicado ?? "—" }}
          </small>
        </div>
        <p v-for="(e, i) in selected.erros_dados" :key="i">
          {{ e.campo }}: {{ e.mensagem }}
        </p>
        <div class="detail-grid">
          <div>
            <dt>Desconto</dt>
            <dd>{{ money(selected.desconto) }}</dd>
          </div>
          <div>
            <dt>Valor líquido</dt>
            <dd>{{ money(selected.valor_liquido) }}</dd>
          </div>
        </div>
        <h3 class="q-mt-lg">Dados originais</h3>
        <dl class="detail-grid">
          <div v-for="(value, key) in selected.dados_originais" :key="key">
            <dt>{{ label(key) }}</dt>
            <dd>{{ value ?? "—" }}</dd>
          </div>
        </dl>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>
