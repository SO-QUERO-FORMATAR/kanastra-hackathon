<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, type DTO } from "../api/client";
import { useCursor } from "../composables/useCursor";
import { money, dateTime } from "../utils";
import { statusLabel } from "../analysisStatus";
import StatusBadge from "../components/StatusBadge.vue";
import ErrorNotice from "../components/ErrorNotice.vue";
import CursorNav from "../components/CursorNav.vue";
import contract from "../../contracts/openapi.json";
const status = ref<DTO<"StatusLote">>();
const { rows, loading, error, next, history, load, forward, back } = useCursor(
  (cursor) => api.lotes({ cursor, limit: 10, status: status.value }),
);
const latest = ref<DTO<"LoteDTO">>();
const statuses = contract.components.schemas.StatusLote.enum.map((value) => ({
  label: statusLabel(value),
  value,
}));
onMounted(async () => {
  await load();
  if (rows.value[0])
    try {
      latest.value = await api.lote(rows.value[0].id);
    } catch {
      /* History remains usable independently of the optional latest summary. */
    }
});
const columns = [
  {
    name: "nome",
    label: "Lote / importação",
    field: "nome",
    align: "left" as const,
  },
  { name: "status", label: "Status", field: "status", align: "left" as const },
  { name: "arquivos_total", label: "Arquivos", field: "arquivos_total" },
  {
    name: "linhas_processadas",
    label: "Linhas analisadas",
    field: "linhas_processadas",
  },
  { name: "total_liquido", label: "Valor líquido", field: "total_liquido" },
  { name: "action", label: "", field: "id" },
];
</script>
<template>
  <div class="page-heading">
    <div>
      <div class="eyebrow">OPERAÇÕES / VISÃO GERAL</div>
      <h1>Recebíveis, sob controle.</h1>
      <p class="subtitle">
        Acompanhe suas importações e transforme dados em decisões.
      </p>
    </div>
    <q-btn color="primary" icon="add" label="Nova importação" to="/novo" />
  </div>
  <section class="hero">
    <div>
      <div class="eyebrow">DO ARQUIVO À DECISÃO</div>
      <h2>
        Mais visibilidade.
        <br />
        Novas possibilidades.
      </h2>
      <p>
        Importe seus recebíveis, acompanhe as validações e consulte cada
        resultado com transparência.
      </p>
      <q-btn
        outline
        color="white"
        label="Importar recebíveis"
        icon-right="arrow_forward"
        to="/novo"
      />
    </div>
  </section>
  <div class="eyebrow">
    {{ latest ? `ÚLTIMO LOTE · ${latest.nome}` : "RESUMO DO ÚLTIMO LOTE" }}
    {{ latest && !latest.resumo.definitivo ? "· PARCIAL" : "" }}
  </div>
  <div class="metrics">
    <div class="metric">
      <div class="metric-label">
        Valor nominal
        <q-icon name="account_balance_wallet" size="17px" />
      </div>
      <div class="metric-value">{{ money(latest?.resumo.total_nominal) }}</div>
      <div class="metric-note">Volume de recebíveis do lote</div>
    </div>
    <div class="metric">
      <div class="metric-label">
        Valor líquido
        <q-icon name="north_east" size="17px" />
      </div>
      <div class="metric-value">{{ money(latest?.resumo.total_liquido) }}</div>
      <div class="metric-note">Após desconto dos aprovados</div>
    </div>
    <div class="metric">
      <div class="metric-label">
        Aprovados
        <q-icon name="check_circle_outline" size="17px" />
      </div>
      <div class="metric-value">
        {{ latest?.resumo.aprovadas.toLocaleString("pt-BR") ?? "—" }}
      </div>
      <div class="metric-note">Recebíveis elegíveis</div>
    </div>
    <div class="metric">
      <div class="metric-label">
        Recusados
        <q-icon name="block" size="17px" />
      </div>
      <div class="metric-value">
        {{ latest?.resumo.barradas.toLocaleString("pt-BR") ?? "—" }}
      </div>
      <div class="metric-note">Consulte os motivos da decisão</div>
    </div>
  </div>
  <ErrorNotice :error="error">
    <q-btn flat label="Tentar novamente" @click="load(true)" />
  </ErrorNotice>
  <section class="surface">
    <div class="surface-head">
      <div>
        <h2>Histórico de importações</h2>
        <p class="subtitle">Todas as etapas de cada lote, em um só lugar.</p>
      </div>
      <q-btn
        flat
        round
        icon="refresh"
        aria-label="Atualizar histórico"
        @click="load(true)"
      />
    </div>
    <div class="filters">
      <q-icon name="filter_list" />
      <q-select
        outlined
        dense
        clearable
        emit-value
        map-options
        v-model="status"
        :options="statuses"
        label="Status do lote"
        @update:model-value="load(true)"
      />
      <q-space />
      <span class="text-caption text-grey-7">Mais recentes primeiro</span>
    </div>
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
      <template #body-cell-nome="p">
        <q-td :props="p">
          <router-link :to="`/lotes/${p.row.id}`" class="table-primary">
            {{ p.row.nome }}
          </router-link>
          <div class="table-secondary">
            {{ dateTime(p.row.criado_em) }}
          </div>
        </q-td>
      </template>
      <template #body-cell-status="p">
        <q-td :props="p"><StatusBadge :status="p.row.status" /></q-td>
      </template>
      <template #body-cell-total_liquido="p">
        <q-td :props="p" class="table-primary">
          {{ money(p.row.total_liquido) }}
        </q-td>
      </template>
      <template #body-cell-action="p">
        <q-td :props="p">
          <q-btn
            flat
            round
            dense
            icon="arrow_forward"
            :to="`/lotes/${p.row.id}`"
            :aria-label="`Abrir ${p.row.nome}`"
          />
        </q-td>
      </template>
    </q-table>
    <div v-if="!loading && !error && rows.length === 0" class="empty">
      Nenhuma importação encontrada. Comece enviando seus arquivos CSV ou XLSX.
    </div>
    <CursorNav
      :next="next"
      :depth="history.length"
      :loading="loading"
      @next="forward"
      @back="back"
    />
  </section>
</template>
