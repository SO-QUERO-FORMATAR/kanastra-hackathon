<script setup lang="ts">
import { ref, shallowRef } from "vue";
import { api, demo, ApiError, type DTO } from "../api/client";
import ErrorNotice from "./ErrorNotice.vue";

const emit = defineEmits<{ imported: [] }>();
const opened = ref(false),
  file = ref<File | null>(null),
  busy = ref(false);
const error = shallowRef<unknown>(null),
  status = ref<DTO<"BaseCadastralStatusResponse">>();
let key = crypto.randomUUID();
function changed() {
  key = crypto.randomUUID();
  error.value = null;
}
async function open() {
  opened.value = true;
  error.value = null;
  try {
    status.value = await api.cadastro();
  } catch (e) {
    error.value = e;
  }
}
async function upload() {
  if (!file.value || busy.value) return;
  busy.value = true;
  error.value = null;
  try {
    if (!file.value.name.toLowerCase().endsWith(".csv"))
      throw Error("Selecione o CSV da base cadastral, não o JSON de regras.");
    if (file.value.size > 1048576)
      throw Error("O CSV cadastral deve ter no máximo 1 MiB.");
    let csv: string;
    try {
      csv = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(
        await file.value.arrayBuffer(),
      );
    } catch {
      throw Error("O CSV cadastral deve estar em UTF-8.");
    }
    await api.importarCadastro({ csv }, key);
    status.value = await api.cadastro();
    if (!status.value.disponivel)
      throw Error("A base ainda não está disponível. Tente novamente.");
    file.value = null;
    changed();
    emit("imported");
    opened.value = false;
  } catch (e) {
    error.value = e;
    // A resolved conflict needs a new logical operation; network retries keep the same key.
    if (
      e instanceof ApiError &&
      e.status === 409 &&
      e.payload?.erro.codigo !== "REQUISICAO_EM_ANDAMENTO"
    )
      key = crypto.randomUUID();
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <div>
    <q-btn
      outline
      icon="upload_file"
      label="Importar base cadastral"
      @click="open"
    />
    <p v-if="status?.disponivel" class="text-positive q-mt-sm" role="status">
      {{ demo ? "Base cadastral simulada" : "Base cadastral disponível" }}:
      {{ status.quantidade_cnpjs }} CNPJ(s).
    </p>
    <q-dialog
      v-model="opened"
      :persistent="busy"
      aria-label="Importar base cadastral"
    >
      <q-card style="width: 600px; max-width: 95vw">
        <q-card-section>
          <h2>Importar base cadastral</h2>
          <p>
            O JSON define as regras dos fundos. Este CSV informa a situação
            cadastral de cada CNPJ e é necessário para analisar as notas.
          </p>
          <p>
            Selecione o arquivo
            <strong>cnpj_situacao_mock.csv</strong>
            fornecido com o projeto ou outro CSV cadastral em UTF-8, com
            cabeçalho
            <code>DOC;SITUACAO_CADASTRAL</code>
            . Limite: 1 MiB.
          </p>
          <p v-if="status?.disponivel">
            Já existe uma base disponível. Uma nova carga substitui a base atual
            para próximas análises; lotes vinculados em andamento impedem a
            substituição.
          </p>
          <p v-if="demo">
            Modo de demonstração: a carga é simulada e não altera o banco.
          </p>
          <q-file
            v-model="file"
            outlined
            accept=".csv,text/csv"
            label="Arquivo CSV cadastral"
            :disable="busy"
            @update:model-value="changed"
          />
          <ErrorNotice :error="error" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Fechar" :disable="busy" v-close-popup />
          <q-btn
            color="primary"
            label="Carregar cadastro"
            :loading="busy"
            :disable="!file"
            @click="upload"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>
