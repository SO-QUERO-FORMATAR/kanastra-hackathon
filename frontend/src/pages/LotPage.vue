<script setup lang="ts">
import { ref, shallowRef, computed, onMounted, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import { api, ApiError, storagePrefix, type DTO } from "../api/client";
import { money } from "../utils";
import { lotMessage, statusLabel } from "../analysisStatus";
import StatusBadge from "../components/StatusBadge.vue";
import ErrorNotice from "../components/ErrorNotice.vue";
import ActionErrorDialog from "../components/ActionErrorDialog.vue";
import ResultsTable from "../components/ResultsTable.vue";
const id = String(useRoute().params.id),
  lot = ref<DTO<"LoteDTO">>(),
  files = ref<DTO<"ArquivoDTO">[]>([]),
  pending = ref<DTO<"PendenciaDTO">[]>([]),
  summaries = ref<DTO<"ResumoFundoDTO">[]>([]),
  selected = ref<string>(),
  error = shallowRef<unknown>(null),
  actionError = shallowRef<unknown>(null),
  resultsRevision = ref(0),
  busy = ref(false);
const selectedFile = computed(() =>
  files.value.find((f) => f.id === selected.value),
);
let timer: ReturnType<typeof setTimeout> | undefined;
let controller: AbortController | undefined;
let disposed = false,
  interval = 2000,
  failures = 0;
let actionKey = localStorage.getItem(`${storagePrefix}process.${id}`) || "";
async function collect<T>(
  fn: (
    cursor?: string,
  ) => Promise<{ itens: T[]; proximo_cursor: string | null }>,
) {
  const out: T[] = [];
  let cursor: string | undefined;
  do {
    const r = await fn(cursor);
    out.push(...r.itens);
    cursor = r.proximo_cursor ?? undefined;
  } while (cursor);
  return out;
}
function schedule(ms: number) {
  clearTimeout(timer);
  if (!disposed && !document.hidden) timer = setTimeout(refresh, ms);
}
async function refresh() {
  clearTimeout(timer);
  if (disposed || document.hidden) return;
  controller?.abort();
  controller = new AbortController();
  const activeController = controller;
  try {
    const previous = lot.value?.status;
    const currentLot = await api.lote(id, activeController.signal);
    const [currentFiles, currentPending, currentSummaries] = await Promise.all([
      collect((c) => api.arquivos(id, c)),
      previous !== currentLot.status || currentLot.status === "BLOQUEADO"
        ? collect((c) => api.pendencias(id, c))
        : Promise.resolve(pending.value),
      collect((c) => api.resumos(id, c)),
    ]);
    if (disposed || activeController.signal.aborted) return;
    lot.value = currentLot;
    files.value = currentFiles;
    pending.value = currentPending;
    summaries.value = currentSummaries;
    if (!files.value.some((f) => f.id === selected.value))
      selected.value = files.value[0]?.id;
    resultsRevision.value++;
    error.value = null;
    failures = 0;
    if (["NA_FILA", "INDEXANDO", "ANALISANDO"].includes(lot.value.status))
      schedule(interval);
  } catch (e) {
    if (disposed || activeController.signal.aborted) return;
    error.value = e;
    if (
      !(e instanceof ApiError) ||
      e.status === 0 ||
      e.payload?.erro.retry_permitido
    )
      schedule(
        Math.max(
          Math.min(interval * 2 ** failures++, 30000),
          e instanceof ApiError ? e.retryAfter : 0,
        ),
      );
  }
}
async function process() {
  if (busy.value) return;
  busy.value = true;
  actionError.value = null;
  try {
    if (!actionKey) {
      actionKey = crypto.randomUUID();
      localStorage.setItem(`${storagePrefix}process.${id}`, actionKey);
    }
    await api.processar(id, actionKey);
    actionKey = "";
    localStorage.removeItem(`${storagePrefix}process.${id}`);
    pending.value = [];
    await refresh();
  } catch (e) {
    actionError.value = e;
    if (
      e instanceof ApiError &&
      e.status === 409 &&
      e.payload?.erro.codigo !== "REQUISICAO_EM_ANDAMENTO"
    ) {
      actionKey = "";
      localStorage.removeItem(`${storagePrefix}process.${id}`);
    }
  } finally {
    busy.value = false;
  }
}
function visibility() {
  if (document.hidden) {
    clearTimeout(timer);
    controller?.abort();
  } else refresh();
}
onMounted(async () => {
  document.addEventListener("visibilitychange", visibility);
  try {
    interval = (await api.capacidades()).polling_intervalo_ms;
  } catch {}
  await refresh();
});
onUnmounted(() => {
  disposed = true;
  clearTimeout(timer);
  controller?.abort();
  document.removeEventListener("visibilitychange", visibility);
});
</script>
<template>
  <div class="page-heading">
    <div>
      <div class="eyebrow">OPERAÇÕES / ACOMPANHAMENTO</div>
      <h1>{{ lot?.nome ?? "Carregando lote…" }}</h1>
      <p class="subtitle">
        Acompanhe o processamento e consulte as decisões da análise.
      </p>
    </div>
    <q-btn flat icon="arrow_back" label="Histórico" to="/" />
  </div>
  <ErrorNotice :error="error">
    <q-btn flat label="Atualizar estado" @click="refresh" />
  </ErrorNotice>
  <ActionErrorDialog
    :error="actionError"
    title="Não foi possível confirmar o início da análise"
    guidance="Volte ao acompanhamento e atualize o estado do lote antes de tentar iniciar ou retomar a análise novamente."
    dismiss-label="Voltar ao acompanhamento"
    @close="actionError = null"
  />
  <template v-if="lot">
    <div class="surface q-pa-lg">
      <div class="row items-center q-gutter-md">
        <StatusBadge
          :status="
            lot.status === 'RECEBENDO' && lot.acoes.pode_iniciar
              ? 'ENVIO_CONCLUIDO'
              : lot.status
          "
        />
        <q-space />
        <q-btn flat icon="refresh" label="Atualizar" @click="refresh" />
        <q-btn
          v-if="lot.acoes.pode_iniciar || lot.acoes.pode_retomar"
          color="primary"
          :label="
            lot.acoes.pode_retomar ? 'Retomar análise' : 'Iniciar análise'
          "
          :loading="busy"
          @click="process"
        />
        <q-btn
          v-if="lot.acoes.pode_enviar_arquivos && !lot.acoes.pode_iniciar"
          outline
          to="/novo"
          label="Retomar envio"
        />
        <q-btn
          v-if="lot.acoes.precisa_recriar_lote"
          outline
          to="/novo"
          label="Criar novo lote"
        />
      </div>
      <p class="subtitle q-mt-md" role="status">{{ lotMessage(lot) }}</p>
      <div class="q-mt-lg text-caption">
        {{ statusLabel(lot.progresso.fase) }} ·
        {{ lot.progresso.arquivos_recebidos }} /
        {{ lot.progresso.arquivos_total }} arquivos recebidos
      </div>
      <q-linear-progress
        class="q-my-md"
        size="7px"
        rounded
        :indeterminate="
          lot.progresso.linhas_total === null &&
          ['NA_FILA', 'INDEXANDO', 'ANALISANDO'].includes(lot.status)
        "
        :value="
          lot.progresso.linhas_total
            ? lot.progresso.linhas_processadas / lot.progresso.linhas_total
            : 0
        "
      />
      <div class="subtitle">
        {{
          lot.progresso.linhas_lidas_primeira_passagem.toLocaleString("pt-BR")
        }}
        linhas lidas na preparação ·
        {{ lot.progresso.linhas_processadas.toLocaleString("pt-BR") }} /
        {{ lot.progresso.linhas_total?.toLocaleString("pt-BR") ?? "—" }}
        analisadas
      </div>
      <q-banner v-if="lot.erro" class="error-banner">
        {{ lot.erro.mensagem }}
      </q-banner>
    </div>
    <div v-if="pending.length" class="surface section-space">
      <div class="surface-head">
        <h2>Pendências para continuar</h2>
        <span class="status-badge pending">
          {{ lot.quantidade_pendencias }} pendência(s)
        </span>
      </div>
      <q-list separator>
        <q-item v-for="(p, i) in pending" :key="i">
          <q-item-section avatar>
            <q-icon name="info_outline" color="warning" />
          </q-item-section>
          <q-item-section>
            {{ p.mensagem }}
            <q-item-label caption>
              {{ p.fundo?.nome }} {{ p.fundo?.cnpj }}
              {{ p.linha ? `· Linha ${p.linha}` : "" }}
              <template v-if="p.acao === 'IMPORTAR_BASE_CADASTRAL'">
                · Solicite a carga cadastral ao responsável pelo backend.
              </template>
            </q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-btn
              v-if="p.acao === 'CONFIGURAR_FUNDO' && p.fundo"
              outline
              label="Configurar fundo"
              :to="`/fundos?fundo=${p.fundo.id}`"
            />
            <q-btn
              v-if="p.acao === 'RECRIAR_LOTE'"
              outline
              label="Nova importação"
              to="/novo"
            />
          </q-item-section>
        </q-item>
      </q-list>
    </div>
    <div class="eyebrow q-mt-lg">
      RESUMO {{ lot.resumo.definitivo ? "DEFINITIVO" : "PARCIAL" }}
    </div>
    <div class="metrics">
      <div
        v-for="(v, k) in {
          Nominal: lot.resumo.total_nominal,
          Líquido: lot.resumo.total_liquido,
          Desconto: lot.resumo.total_desconto,
        }"
        :key="k"
        class="metric"
      >
        <div class="metric-label">{{ k }}</div>
        <div class="metric-value">{{ money(v) }}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Resultados</div>
        <div class="q-mt-md text-caption">
          {{ lot.resumo.aprovadas }} aprovados ·
          {{ lot.resumo.barradas }} recusados
          <br />
          {{ lot.resumo.erros_dados }}
          linhas com dados inválidos
        </div>
      </div>
    </div>
    <div v-if="summaries.length" class="surface section-space">
      <div class="surface-head"><h2>Resumo por fundo</h2></div>
      <q-list separator>
        <q-item v-for="s in summaries" :key="s.fundo.id">
          <q-item-section>
            {{ s.fundo.nome }}
            <q-item-label caption>
              PL {{ money(s.pl) }} · Limite sacado
              {{ money(s.limite_sacado) }} · Limite cedente
              {{ money(s.limite_cedente) }}
            </q-item-label>
            <q-item-label caption>
              Líquido {{ money(s.resumo.total_liquido) }} ·
              {{ s.resumo.definitivo ? "Definitivo" : "Parcial" }}
            </q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-btn
              v-if="s.versao_regras_utilizada"
              flat
              label="Regras utilizadas"
              :to="{
                path: '/fundos',
                query: { fundo: s.fundo.id, versao: s.versao_regras_utilizada },
              }"
            />
          </q-item-section>
        </q-item>
      </q-list>
    </div>
    <div class="section-space">
      <q-select
        outlined
        v-model="selected"
        :options="
          files.map((f) => ({
            label: `${f.nome} · ${statusLabel(f.status)}`,
            value: f.id,
          }))
        "
        emit-value
        map-options
        label="Arquivo para consulta"
      />
      <q-banner
        v-if="files.find((f) => f.id === selected)?.erro"
        class="error-banner"
      >
        {{ files.find((f) => f.id === selected)?.erro?.mensagem }}
      </q-banner>
    </div>
    <ResultsTable
      v-if="selected"
      :arquivo-id="selected"
      :file-status="selectedFile?.status"
      :lot-status="lot.status"
      :refresh-revision="resultsRevision"
    />
  </template>
</template>
