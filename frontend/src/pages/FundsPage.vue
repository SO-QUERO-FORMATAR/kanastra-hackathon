<script setup lang="ts">
import { ref, shallowRef, onMounted, computed, nextTick } from "vue";
import { useQuasar } from "quasar";
import { ruleMutationKey } from "../api/idempotency";
import { useRoute } from "vue-router";
import { api, ApiError, type DTO } from "../api/client";
import { useCursor } from "../composables/useCursor";
import { label } from "../utils";
import ErrorNotice from "../components/ErrorNotice.vue";
import ActionErrorDialog from "../components/ActionErrorDialog.vue";
import CursorNav from "../components/CursorNav.vue";
import examples from "../../contracts/examples.json";
import { ruleFieldErrors, validateRules } from "../ruleValidation";
const $q = useQuasar();
const importFile = ref<File | null>(null),
  importing = ref(false),
  importError = shallowRef<unknown>(null);
let importKey = crypto.randomUUID();
function selectImport() {
  importKey = crypto.randomUUID();
  importError.value = null;
}
async function importRules() {
  if (!importFile.value || importing.value) return;
  importing.value = true;
  importError.value = null;
  try {
    if (!importFile.value.name.toLowerCase().endsWith(".json"))
      throw Error("Selecione um arquivo JSON de regras.");
    if (importFile.value.size > 1048576)
      throw Error("O JSON deve ter no máximo 1 MiB.");
    let body: DTO<"ImportarRegrasRequest">;
    try {
      body = JSON.parse((await importFile.value.text()).replace(/^\uFEFF/, ""));
    } catch {
      throw Error("O arquivo não contém um JSON válido.");
    }
    const result = await api.importarRegras(body, importKey);
    importFile.value = null;
    selectImport();
    busca.value = "";
    configurado.value = undefined;
    await load(true);
    $q.notify({
      type: "positive",
      message: `Regras importadas para ${result.fundos.length} fundo(s).`,
      position: "top",
    });
  } catch (e) {
    importError.value = e;
  } finally {
    importing.value = false;
  }
}
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
  actionError = shallowRef<unknown>(null),
  attempted = ref(false),
  formError = ref(""),
  rulesSection = ref<HTMLElement>(),
  saving = ref(false),
  conflict = ref(false),
  historical = ref(false),
  reviewed = ref(false);
const fieldErrors = computed(() =>
  attempted.value && form.value ? ruleFieldErrors(form.value) : {},
);
function fieldError(path: string) {
  return (
    Object.entries(fieldErrors.value).find(
      ([key]) => key === path || key.startsWith(path + "/"),
    )?.[1] || ""
  );
}
function showConflict() {
  actionError.value = Error("Outra edição alterou as regras deste fundo.");
}
async function reloadRules() {
  if (!selected.value || saving.value) return;
  // Fetch before replacing the local values so a failed reload preserves edits.
  saving.value = true;
  try {
    const r = await api.regras(selected.value.id);
    form.value = { versao_base: r.versao, configuracao: r.configuracao };
    hydrateParameters();
    conflict.value = false;
    reviewed.value = false;
    attempted.value = false;
    formError.value = "";
    actionError.value = null;
  } catch (e) {
    actionError.value = e;
  } finally {
    saving.value = false;
  }
}
async function open(f: DTO<"FundoDTO">, version?: string) {
  if (saving.value) return;
  selected.value = f;
  form.value = undefined;
  editError.value = null;
  actionError.value = null;
  attempted.value = false;
  formError.value = "";
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
  hydrateParameters();
}
function hydrateParameters() {
  // Inactive imported rules can omit parameters; expose empty editable fields
  // when they are enabled, without copying another fund's business values.
  if (form.value && !historical.value) {
    for (const v of form.value.configuracao.validadores) {
      const template = examples.ConfiguracaoRegrasDTO.validadores.find(
        (t) => t.codigo === v.codigo,
      );
      for (const [key, value] of Object.entries(template?.parametros ?? {})) {
        if (!(key in v.parametros))
          v.parametros[key] =
            key === "agrupamento"
              ? "RAIZ_CNPJ"
              : Array.isArray(value)
                ? []
                : typeof value === "number"
                  ? 0
                  : "";
      }
    }
  }
}
function param(v: DTO<"ValidadorDTO">, key: string, value: unknown) {
  (v.parametros as Record<string, unknown>)[key] = value;
}
async function save() {
  if (
    !form.value ||
    !selected.value ||
    saving.value ||
    conflict.value ||
    historical.value ||
    !reviewed.value
  )
    return;
  editError.value = null;
  attempted.value = true;
  formError.value = "";
  if (!validateRules(form.value)) {
    if (!Object.keys(fieldErrors.value).length)
      formError.value =
        "Revise a configuração dos nove validadores antes de salvar.";
    await nextTick();
    const target = rulesSection.value?.querySelector<HTMLElement>(
      ".q-field--error input, .q-field--error [tabindex='0'], [data-form-error]",
    );
    target?.focus();
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
    attempted.value = false;
    $q.notify({
      type: "positive",
      message: "Configuração salva com sucesso.",
      position: "top",
      timeout: 4000,
    });
    await load();
  } catch (e) {
    actionError.value = e;
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
  <ErrorNotice :error="error">
    <q-btn flat label="Tentar carregar novamente" @click="load()" />
  </ErrorNotice>
  <div class="surface q-pa-lg q-mb-lg">
    <h2>Importar regras de fundos</h2>
    <p class="subtitle">
      Selecione o JSON de inputs com fundo, validadores e precificação. Aceita
      um fundo ou uma lista de até 100 fundos. As configurações dos fundos
      presentes no arquivo serão atualizadas.
    </p>
    <div class="row items-start q-gutter-md q-mt-sm">
      <q-file
        v-model="importFile"
        outlined
        dense
        accept=".json,application/json"
        label="Arquivo JSON de regras"
        :disable="importing"
        @update:model-value="selectImport"
      />
      <q-btn
        color="primary"
        icon="upload_file"
        label="Importar regras"
        :loading="importing"
        :disable="!importFile"
        @click="importRules"
      />
    </div>
    <ErrorNotice :error="importError" />
  </div>
  <ActionErrorDialog
    :error="actionError"
    :title="
      conflict
        ? 'As regras foram alteradas'
        : 'Não foi possível salvar a configuração'
    "
    :guidance="
      conflict
        ? 'Sua edição foi mantida. Carregar a versão atual substituirá os valores locais. Depois, revise as regras antes de salvar.'
        : 'Sua edição foi mantida. Feche este aviso para revisar os valores e tentar novamente.'
    "
    :dismiss-label="conflict ? 'Manter minha edição' : 'Voltar à edição'"
    :action-label="conflict ? 'Carregar versão atual' : undefined"
    :loading="saving"
    @close="actionError = null"
    @action="reloadRules"
  />
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
    <div v-if="!rows.length && !loading && !error" class="empty">
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
  <q-dialog
    :model-value="!!selected"
    :persistent="saving"
    aria-labelledby="fund-rules-title"
    @update:model-value="!$event && (selected = undefined)"
  >
    <q-card class="fund-rules-dialog">
      <section v-if="selected" ref="rulesSection">
        <div class="surface-head">
          <div>
            <h2 id="fund-rules-title">{{ selected.nome }}</h2>
            <p class="subtitle">
              {{
                historical
                  ? "Versão histórica · somente leitura"
                  : "Alterações valem para novas análises deste fundo."
              }}
            </p>
          </div>
          <q-btn
            flat
            icon="close"
            aria-label="Fechar regras"
            :disable="saving"
            @click="selected = undefined"
          />
        </div>
        <ErrorNotice :error="editError">
          <q-btn
            flat
            label="Tentar carregar regras novamente"
            @click="
              open(
                selected,
                historical ? String(route.query.versao) : undefined,
              )
            "
          />
        </ErrorNotice>
        <q-banner
          v-if="formError"
          class="error-banner"
          role="alert"
          tabindex="-1"
          data-form-error
        >
          {{ formError }}
        </q-banner>
        <div v-if="conflict" class="q-pa-lg">
          <p>
            Outra edição alterou as regras. Recarregue a versão atual e revise
            antes de salvar novamente.
          </p>
          <q-btn
            outline
            label="Recarregar configuração"
            :disable="saving"
            @click="showConflict"
          />
        </div>
        <template v-if="form">
          <div class="q-pa-lg info-banner">
            Duplicidade de notas é verificada sempre. Cada fundo exige
            configuração explícita; regras não são copiadas de outros fundos.
          </div>
          <div
            v-for="(v, index) in form.configuracao.validadores"
            :key="v.codigo"
            class="rule-row"
          >
            <q-toggle
              v-model="v.ativo"
              :label="label(v.codigo)"
              :disable="historical || saving"
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
                  :disable="!v.ativo || historical || saving"
                  :error="
                    !!fieldError(`/validadores/${index}/parametros/${key}`)
                  "
                  :error-message="
                    fieldError(`/validadores/${index}/parametros/${key}`)
                  "
                  @update:model-value="param(v, String(key), $event)"
                />
                <q-input
                  v-else
                  outlined
                  dense
                  :model-value="
                    typeof value === 'number' ? value : String(value ?? '')
                  "
                  :label="label(String(key))"
                  :readonly="key === 'agrupamento' || historical || saving"
                  :disable="!v.ativo"
                  :error="
                    !!fieldError(`/validadores/${index}/parametros/${key}`)
                  "
                  :error-message="
                    fieldError(`/validadores/${index}/parametros/${key}`)
                  "
                  :type="typeof value === 'number' ? 'number' : 'text'"
                  @update:model-value="
                    param(
                      v,
                      String(key),
                      typeof value === 'number'
                        ? Number($event)
                        : String($event),
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
                :readonly="historical || saving"
                :error="!!fieldError('/precificacao/taxa_mensal_percentual')"
                :error-message="
                  fieldError('/precificacao/taxa_mensal_percentual')
                "
              />
              <q-input
                outlined
                type="number"
                v-model.number="form.configuracao.precificacao.base_dias"
                label="Base de dias (1–366)"
                :readonly="historical || saving"
                :error="!!fieldError('/precificacao/base_dias')"
                :error-message="fieldError('/precificacao/base_dias')"
              />
            </div>
            <div class="text-caption text-grey-7 q-my-md">
              Versão base: {{ form.versao_base ?? "Primeira configuração" }}
            </div>
            <template v-if="!historical">
              <q-checkbox
                v-model="reviewed"
                :disable="saving"
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
    </q-card>
  </q-dialog>
</template>
<style scoped>
.fund-rules-dialog {
  width: 960px;
  max-width: 95vw;
  max-height: 90vh;
  overflow-y: auto;
}
.fund-rules-dialog .surface-head {
  position: sticky;
  top: 0;
  background: white;
  z-index: 2;
}
</style>
