<script setup lang="ts">
import { ref, shallowRef, onMounted } from "vue";
import { ruleMutationKey } from "../api/idempotency";
import { useRoute } from "vue-router";
import { api, ApiError, type DTO } from "../api/client";
import { useCursor } from "../composables/useCursor";
import { label } from "../utils";
import ErrorNotice from "../components/ErrorNotice.vue";
import CursorNav from "../components/CursorNav.vue";
import examples from "../../contracts/examples.json";
import Ajv from "ajv/dist/2020";
import addFormats from "ajv-formats";
import contract from "../../contracts/openapi.json";
const ajv = new Ajv({ strict: false });
addFormats(ajv);
ajv.addSchema(contract, "contract");
const validate = ajv.compile({
  $ref: "contract#/components/schemas/AtualizarRegrasRequest",
});
const busca = ref(""),
  configurado = ref<boolean>(),
  route = useRoute();
const { rows, loading, error, next, history, load, forward, back } = useCursor(
  (cursor) =>
    api.fundos({
      busca: busca.value || undefined,
      configurado: configurado.value,
      cursor,
      limit: 20,
    }),
);
const selected = ref<DTO<"FundoDTO">>(),
  form = ref<DTO<"AtualizarRegrasRequest">>(),
  editError = shallowRef<unknown>(null),
  saving = ref(false),
  conflict = ref(false),
  historical = ref(false),
  reviewed = ref(false);
async function open(f: DTO<"FundoDTO">, version?: string) {
  selected.value = f;
  form.value = undefined;
  editError.value = null;
  conflict.value = false;
  reviewed.value = false;
  historical.value = !!version;
  try {
    if (f.configurado || version) {
      const r = await api.regras(f.id, version);
      form.value = { versao_base: r.versao, configuracao: r.configuracao };
    } else {
      const conf = structuredClone(
        examples.ConfiguracaoRegrasDTO,
      ) as DTO<"ConfiguracaoRegrasDTO">;
      conf.validadores.forEach((v) => {
        v.ativo = false;
        Object.entries(v.parametros).forEach(([k, vv]) => {
          (v.parametros as Record<string, unknown>)[k] =
            k === "agrupamento"
              ? "RAIZ_CNPJ"
              : Array.isArray(vv)
                ? []
                : typeof vv === "number"
                  ? 0
                  : "";
        });
      });
      conf.precificacao = {
        metodo: "DESCONTO_SIMPLES",
        taxa_mensal_percentual: "",
        base_dias: 30,
      };
      form.value = { versao_base: null, configuracao: conf };
    }
  } catch (e) {
    editError.value = e;
  }
}
function param(v: DTO<"ValidadorDTO">, key: string, value: unknown) {
  (v.parametros as Record<string, unknown>)[key] = value;
}
async function save() {
  if (!form.value || !selected.value) return;
  editError.value = null;
  if (!validate(form.value)) {
    editError.value = Error(
      (validate.errors || [])
        .map((e) => `${e.instancePath}: ${e.message}`)
        .join("; "),
    );
    return;
  }
  saving.value = true;
  try {
    const r = await api.salvarRegras(
      selected.value.id,
      form.value,
      ruleMutationKey(selected.value.id, form.value),
    );
    form.value = { versao_base: r.versao, configuracao: r.configuracao };
    selected.value = r.fundo;
    reviewed.value = false;
    await load();
  } catch (e) {
    editError.value = e;
    conflict.value =
      e instanceof ApiError &&
      e.payload?.erro.codigo === "VERSAO_REGRAS_CONFLITANTE";
  } finally {
    saving.value = false;
  }
}
onMounted(async () => {
  await load();
  const id = route.query.fundo as string | undefined;
  if (id) {
    let found = rows.value.find((f) => f.id === id);
    while (!found && next.value) {
      await forward();
      found = rows.value.find((f) => f.id === id);
    }
    if (found) await open(found, route.query.versao as string | undefined);
  }
});
</script>
<template>
  <div class="page-heading">
    <div>
      <div class="eyebrow">CONFIGURAÇÃO / FUNDOS</div>
      <h1>Cada fundo, suas regras.</h1>
      <p class="subtitle">
        Configure os critérios de elegibilidade e a precificação de forma
        independente.
      </p>
    </div>
  </div>
  <ErrorNotice :error="error" />
  <div class="surface">
    <div class="filters">
      <q-input
        outlined
        dense
        v-model="busca"
        label="Buscar nome ou CNPJ"
        @keyup.enter="load(true)"
      >
        <template #append>
          <q-btn
            flat
            dense
            icon="search"
            aria-label="Buscar fundos"
            @click="load(true)"
          />
        </template>
      </q-input>
      <q-select
        outlined
        dense
        clearable
        v-model="configurado"
        emit-value
        map-options
        :options="[
          { label: 'Configurados', value: true },
          { label: 'Pendentes', value: false },
        ]"
        label="Configuração"
        @update:model-value="load(true)"
      />
    </div>
    <q-list separator>
      <q-item v-for="f in rows" :key="f.id" clickable @click="open(f)">
        <q-item-section avatar>
          <q-icon name="account_balance" color="primary" />
        </q-item-section>
        <q-item-section>
          <q-item-label class="table-primary">{{ f.nome }}</q-item-label>
          <q-item-label caption>{{ f.cnpj }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <span
            class="status-badge"
            :class="f.configurado ? 'positive' : 'pending'"
          >
            {{ f.configurado ? "Configurado" : "Configuração pendente" }}
          </span>
        </q-item-section>
        <q-item-section side><q-icon name="chevron_right" /></q-item-section>
      </q-item>
    </q-list>
    <div v-if="!rows.length && !loading" class="empty">
      Nenhum fundo encontrado.
    </div>
    <q-linear-progress v-if="loading" indeterminate />
    <CursorNav
      :next="next"
      :depth="history.length"
      :loading="loading"
      @next="forward"
      @back="back"
    />
  </div>
  <section v-if="selected" class="surface section-space">
    <div class="surface-head">
      <div>
        <h2>{{ selected.nome }}</h2>
        <p class="subtitle">
          {{
            historical
              ? "Versão histórica · somente leitura"
              : "Alterações valem para lotes que ainda não iniciaram a análise."
          }}
        </p>
      </div>
      <q-btn
        flat
        icon="close"
        aria-label="Fechar regras"
        @click="selected = undefined"
      />
    </div>
    <ErrorNotice :error="editError" />
    <div v-if="conflict" class="q-pa-lg">
      <p>
        Outra edição alterou as regras. Recarregue a versão atual e revise antes
        de salvar novamente.
      </p>
      <q-btn outline label="Recarregar configuração" @click="open(selected)" />
    </div>
    <template v-if="form">
      <div class="q-pa-lg info-banner">
        Duplicidade de notas é verificada sempre. Cada fundo exige configuração
        explícita; regras não são copiadas de outros fundos.
      </div>
      <div
        v-for="v in form.configuracao.validadores"
        :key="v.codigo"
        class="rule-row"
      >
        <q-toggle
          v-model="v.ativo"
          :label="label(v.codigo)"
          :disable="historical"
        />
        <div class="rule-fields">
          <template v-for="(value, key) in v.parametros" :key="key">
            <q-select
              v-if="Array.isArray(value)"
              outlined
              dense
              multiple
              use-input
              use-chips
              new-value-mode="add-unique"
              :model-value="value"
              :options="[]"
              :label="label(String(key)) + ' (Enter para adicionar)'"
              :disable="historical"
              @update:model-value="param(v, String(key), $event)"
            />
            <q-input
              v-else
              outlined
              dense
              :model-value="value"
              :label="label(String(key))"
              :readonly="key === 'agrupamento' || historical"
              :type="typeof value === 'number' ? 'number' : 'text'"
              @update:model-value="
                param(
                  v,
                  String(key),
                  typeof value === 'number' ? Number($event) : String($event),
                )
              "
            />
          </template>
        </div>
      </div>
      <div class="q-pa-lg">
        <h3>Precificação · Desconto simples</h3>
        <div class="rule-fields">
          <q-input
            outlined
            v-model="form.configuracao.precificacao.taxa_mensal_percentual"
            label="Taxa mensal (%)"
            :readonly="historical"
          />
          <q-input
            outlined
            type="number"
            v-model.number="form.configuracao.precificacao.base_dias"
            label="Base de dias (1–366)"
            :readonly="historical"
          />
        </div>
        <div class="text-caption text-grey-7 q-my-md">
          Versão base: {{ form.versao_base ?? "Primeira configuração" }}
        </div>
        <template v-if="!historical">
          <q-checkbox
            v-model="reviewed"
            label="Revisei os nove validadores e a precificação deste fundo."
          />
          <div class="q-mt-md">
            <q-btn
              color="primary"
              label="Salvar configuração"
              :loading="saving"
              :disable="!reviewed || conflict"
              @click="save"
            />
          </div>
        </template>
      </div>
    </template>
    <q-spinner v-else-if="!editError" class="q-ma-lg" />
  </section>
</template>
