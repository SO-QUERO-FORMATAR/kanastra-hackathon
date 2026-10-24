<script setup lang="ts">
import { ref, watch, computed, onUnmounted } from "vue";
import { api, type DTO } from "../api/client";
import { useCursor } from "../composables/useCursor";
import { money, label } from "../utils";
import { isTerminal, resultMessage, refusalLabels } from "../analysisStatus";
import StatusBadge from "./StatusBadge.vue";
import ErrorNotice from "./ErrorNotice.vue";
import CursorNav from "./CursorNav.vue";
import contract from "../../contracts/openapi.json";
const props = defineProps<{
    arquivoId: string;
    fileStatus?: DTO<"StatusArquivo">;
    lotStatus: DTO<"StatusLote">;
    refreshRevision: number;
  }>(),
  filter = ref("TODOS"),
  motivo = ref<DTO<"CodigoRecusa">>(),
  limit = ref(20),
  selected = ref<DTO<"ResultadoDTO">>(),
  finished = ref(false),
  updateAvailable = ref(false),
  returnedToFirst = ref(false);
let requestVersion = 0,
  disposed = false,
  queuedRefresh = false;
const { rows, loading, error, next, history, load, forward, back } = useCursor(
  async (cursor) => {
    const run = ++requestVersion;
    const q: DTO<"ListarResultadosQuery"> = { cursor, limit: limit.value };
    if (filter.value === "ERRO_DADOS") q.tipo = "ERRO_DADOS";
    else if (filter.value !== "TODOS")
      q.status = filter.value as DTO<"StatusNota">;
    if (filter.value !== "ERRO_DADOS" && filter.value !== "APROVADO")
      q.motivo = motivo.value;
    const r = await api.resultados(props.arquivoId, q);
    if (!disposed && run === requestVersion)
      finished.value = r.arquivo_finalizado;
    return r;
  },
);
function reload() {
  queuedRefresh = false;
  updateAvailable.value = false;
  return load(true);
}
function autoRefresh() {
  if (loading.value) queuedRefresh = true;
  else void reload();
}
watch(
  () =>
    [
      props.arquivoId,
      props.refreshRevision,
      isTerminal(props.fileStatus) || isTerminal(props.lotStatus),
    ] as const,
  ([id, , terminal], previous) => {
    if (!previous || id !== previous[0]) {
      selected.value = undefined;
      finished.value = false;
      returnedToFirst.value = false;
      void reload();
    } else if (terminal && !previous[2]) {
      returnedToFirst.value = history.value.length > 1;
      autoRefresh();
    } else if (history.value.length === 1) autoRefresh();
    else updateAvailable.value = true;
  },
  { immediate: true },
);
watch(loading, (active) => {
  if (!active && queuedRefresh && !disposed) void reload();
});
onUnmounted(() => {
  disposed = true;
  requestVersion++;
});
watch(filter, () => {
  motivo.value = undefined;
  reload();
});
const hasFilters = computed(() => filter.value !== "TODOS" || !!motivo.value);
const statusMessage = computed(() => {
  if (props.fileStatus === "FALHOU")
    return "O processamento deste arquivo foi interrompido. Consulte o erro acima; os resultados podem estar incompletos.";
  if (props.fileStatus === "CONCLUIDO_COM_ERROS")
    return "Arquivo processado com erros nos dados. Consulte as linhas com dados inválidos e os diagnósticos do arquivo.";
  if (props.fileStatus === "CONCLUIDO")
    return "Análise deste arquivo concluída. Os resultados estão disponíveis para consulta.";
  if (props.lotStatus === "FALHOU")
    return "O processamento do lote foi interrompido. Os resultados disponíveis podem estar incompletos.";
  if (finished.value)
    return "Processamento deste arquivo encerrado. Consulte as decisões e os diagnósticos disponíveis.";
  if (props.lotStatus === "BLOQUEADO")
    return "A análise aguarda a correção das pendências do lote. Os resultados disponíveis são parciais.";
  if (props.lotStatus === "RECEBENDO")
    return "Os resultados aparecerão após o envio dos arquivos e o início da análise.";
  if (props.lotStatus === "NA_FILA")
    return "Análise na fila. A tabela será atualizada automaticamente quando houver resultados.";
  if (props.lotStatus === "INDEXANDO")
    return "Preparando os dados. A tabela será atualizada automaticamente durante o processamento.";
  return "Resultados parciais. A primeira página é atualizada automaticamente durante a análise.";
});
const emptyMessage = computed(() => {
  if (loading.value) return "Carregando resultados…";
  if (error.value)
    return "Não foi possível carregar os resultados. Tente novamente no aviso acima.";
  if (hasFilters.value)
    return "Nenhum resultado corresponde aos filtros selecionados nesta consulta.";
  if (
    isTerminal(props.fileStatus) ||
    isTerminal(props.lotStatus) ||
    finished.value
  )
    return "Nenhum resultado disponível para este arquivo. Consulte o status e os diagnósticos acima.";
  return statusMessage.value;
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
  label: refusalLabels[value as DTO<"CodigoRecusa">],
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
      <q-btn
        flat
        icon="refresh"
        label="Atualizar resultados"
        :loading="loading"
        @click="reload"
      />
    </div>
    <div class="filters">
      <q-select
        outlined
        dense
        v-model="filter"
        :options="[
          { label: 'Todos os resultados', value: 'TODOS' },
          { label: 'Aprovados', value: 'APROVADO' },
          { label: 'Recusados', value: 'BARRADO' },
          { label: 'Dados inválidos', value: 'ERRO_DADOS' },
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
        @update:model-value="reload"
      />
      <q-select
        outlined
        dense
        v-model="limit"
        :options="[10, 20, 50, 100]"
        label="Itens por página"
        @update:model-value="reload"
      />
    </div>
    <ErrorNotice :error="error">
      <q-btn flat label="Reiniciar consulta" @click="reload" />
    </ErrorNotice>
    <q-banner v-if="updateAvailable" class="info-banner" role="status">
      O acompanhamento foi atualizado. Consulte a primeira página para carregar
      os resultados mais recentes.
      <q-btn flat label="Carregar resultados recentes" @click="reload" />
    </q-banner>
    <p v-if="returnedToFirst" class="q-px-lg text-caption" role="status">
      Processamento encerrado. A tabela voltou à primeira página para exibir a
      consulta atualizada, mantendo seus filtros.
    </p>
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
      <template #no-data>
        <div class="empty full-width" role="status">{{ emptyMessage }}</div>
      </template>
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
            {{ resultMessage(p.row) }}
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
    <div
      v-if="!error"
      class="q-px-lg q-py-sm text-caption text-grey-7"
      role="status"
    >
      {{ statusMessage }}
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
          <strong>{{ refusalLabels[m.codigo] }}</strong>
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
