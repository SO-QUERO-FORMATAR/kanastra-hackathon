<script setup lang="ts">
import { ref, onMounted, shallowRef, computed, nextTick } from "vue";
import { useQuasar, type QInput } from "quasar";
import { useRouter } from "vue-router";
import { api, upload, storagePrefix, demo, type DTO } from "../api/client";
import { sha256, batches } from "../utils";
import ErrorNotice from "../components/ErrorNotice.vue";
import RegistryImport from "../components/RegistryImport.vue";
import ActionErrorDialog from "../components/ActionErrorDialog.vue";
const $q = useQuasar();
const router = useRouter(),
  files = ref<File[]>([]),
  name = ref(""),
  caps = ref<DTO<"CapacidadesResponse">>(),
  cadastro = ref<DTO<"BaseCadastralStatusResponse">>(),
  error = shallowRef<unknown>(null),
  actionError = shallowRef<unknown>(null),
  mismatch = ref(false),
  submitted = ref(false),
  nameTouched = ref(false),
  nameInput = ref<QInput>(),
  fileArea = ref<HTMLElement>(),
  busy = ref(false),
  progress = ref(0),
  phase = ref(""),
  locked = ref(false),
  input = ref<HTMLInputElement>();
type Session = {
  key: string;
  body: DTO<"CriarLoteRequest">;
  created?: DTO<"CriarLoteResponse">;
  batches?: { ids: string[]; key: string }[];
};
let session: Session | undefined;
const nameError = computed(() => {
  if (!submitted.value && !nameTouched.value) return "";
  if (!name.value.trim()) return "Informe o nome do lote.";
  return name.value.trim().length > 120
    ? "Use até 120 caracteres no nome do lote."
    : "";
});
const selectionError = computed(() => {
  if (!files.value.length && submitted.value)
    return "Selecione pelo menos um arquivo.";
  if (caps.value && files.value.length > caps.value.max_arquivos_lote)
    return `Selecione no máximo ${caps.value.max_arquivos_lote} arquivos. Remova os arquivos excedentes.`;
  return "";
});
function fileError(file: File) {
  const c = caps.value;
  if (!c) return "";
  if (
    !c.formatos.includes(
      file.name.split(".").at(-1)?.toUpperCase() as DTO<"FormatoArquivo">,
    )
  )
    return `Formato não permitido. Selecione ${c.formatos.join(" ou ")}.`;
  if (!file.size)
    return "Este arquivo está vazio. Selecione um arquivo com dados.";
  const limit = Math.min(c.max_bytes_arquivo, c.max_bytes_batch);
  return file.size > limit
    ? `O arquivo excede o limite de ${limit / 1048576} MiB. Reduza o tamanho antes de enviar.`
    : "";
}
async function loadSetup() {
  error.value = null;
  try {
    [caps.value, cadastro.value] = await Promise.all([
      api.capacidades(),
      api.cadastro(),
    ]);
  } catch (e) {
    error.value = e;
  }
}
onMounted(loadSetup);
function select(list: FileList | null) {
  if (!busy.value && list)
    files.value = locked.value
      ? Array.from(list)
      : [...files.value, ...Array.from(list)];
  if (input.value) input.value.value = "";
}
function persist() {
  localStorage.setItem(storagePrefix + "upload", JSON.stringify(session));
}
const stored = localStorage.getItem(storagePrefix + "upload");
if (stored) {
  try {
    session = JSON.parse(stored);
    name.value = session!.body.nome;
    locked.value = true;
  } catch {
    localStorage.removeItem(storagePrefix + "upload");
  }
}
function reset() {
  session = undefined;
  files.value = [];
  locked.value = false;
  submitted.value = false;
  nameTouched.value = false;
  progress.value = 0;
  phase.value = "";
  if (input.value) input.value.value = "";
  localStorage.removeItem(storagePrefix + "upload");
  actionError.value = null;
}
function confirmReset() {
  $q.dialog({
    title: "Iniciar uma nova seleção?",
    message:
      "A recuperação deste envio será removida deste navegador. Os arquivos já recebidos pelo servidor não serão excluídos.",
    cancel: { label: "Manter envio", flat: true },
    ok: { label: "Iniciar nova seleção", color: "primary" },
    focus: "cancel",
  }).onOk(reset);
}
async function closeError() {
  actionError.value = null;
  if (mismatch.value) {
    await nextTick();
    fileArea.value?.focus();
  }
}
async function submit() {
  if (!caps.value || busy.value) return;
  submitted.value = true;
  if (nameError.value) {
    await nextTick();
    nameInput.value?.focus();
    return;
  }
  if (selectionError.value || files.value.some(fileError)) {
    await nextTick();
    fileArea.value?.focus();
    return;
  }
  busy.value = true;
  actionError.value = null;
  mismatch.value = false;
  progress.value = 0;
  try {
    const c = caps.value;
    phase.value = "Verificando integridade dos arquivos";
    const manifest: DTO<"ArquivoManifestoRequest">[] = [];
    for (const [i, file] of files.value.entries()) {
      const ext = file.name.split(".").at(-1)?.toUpperCase();
      manifest.push({
        client_id: session?.body.arquivos[i]?.client_id || crypto.randomUUID(),
        nome: file.name,
        formato: ext as DTO<"FormatoArquivo">,
        tamanho_bytes: file.size,
        sha256: await sha256(file),
        ordem: i,
        aba: null,
      });
    }
    if (
      session &&
      JSON.stringify(manifest) !== JSON.stringify(session.body.arquivos)
    ) {
      mismatch.value = true;
      throw Error(
        "Para retomar, selecione exatamente os mesmos arquivos na ordem original. Ou inicie uma nova seleção.",
      );
    }
    if (!session) {
      session = {
        key: crypto.randomUUID(),
        body: { nome: name.value.trim(), arquivos: manifest },
      };
      persist();
    }
    locked.value = true;
    phase.value = "Criando lote";
    if (!session.created) {
      session.created = await api.criar(session.body, session.key);
      persist();
    }
    const created = session.created;
    if (!session.batches) {
      session.batches = batches(
        created.arquivos,
        c.max_arquivos_batch,
        c.max_bytes_batch,
      ).map((group) => ({
        ids: group.map((x) => x.id),
        key: crypto.randomUUID(),
      }));
      persist();
    }
    let confirmed: DTO<"ArquivoDTO">[] = [];
    let cursor: string | undefined;
    do {
      const page = await api.arquivos(created.lote.id, cursor);
      confirmed.push(...page.itens);
      cursor = page.proximo_cursor ?? undefined;
    } while (cursor);
    for (const [index, batch] of session.batches.entries()) {
      if (
        batch.ids.every((id) =>
          confirmed.some(
            (f) => f.id === id && f.bytes_recebidos === f.tamanho_bytes,
          ),
        )
      )
        continue;
      phase.value = `Enviando batch ${index + 1} de ${session.batches.length}`;
      await upload(
        created.lote.id,
        batch.ids.map((id) => {
          const a = created.arquivos.find((f) => f.id === id)!;
          return {
            id,
            file: files.value[
              manifest.findIndex((m) => m.client_id === a.client_id)
            ]!,
          };
        }),
        batch.key,
        (p) => (progress.value = (index + p) / session!.batches!.length),
      );
    }
    progress.value = 1;
    localStorage.setItem(
      storagePrefix + "upload." + created.lote.id,
      JSON.stringify(session),
    );
    localStorage.removeItem(storagePrefix + "upload");
    await router.push(`/lotes/${created.lote.id}`);
  } catch (e) {
    actionError.value = e;
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <div class="page-heading">
    <div>
      <div class="eyebrow">OPERAÇÕES / NOVA IMPORTAÇÃO</div>
      <h1>O próximo passo começa aqui.</h1>
      <p class="subtitle">
        Envie seus recebíveis para análise das regras de cada fundo.
      </p>
    </div>
    <q-btn flat icon="arrow_back" label="Voltar" to="/" />
  </div>
  <q-banner v-if="demo" class="info-banner q-mb-lg">
    Demonstração: o envio é simulado. Os resultados são exemplos fixos e não
    correspondem ao conteúdo selecionado.
  </q-banner>
  <ErrorNotice :error="error">
    <q-btn flat label="Tentar carregar novamente" @click="loadSetup" />
  </ErrorNotice>
  <ActionErrorDialog
    :error="actionError"
    :title="
      mismatch
        ? 'Os arquivos são diferentes do envio original'
        : 'Não foi possível concluir o envio'
    "
    :guidance="
      mismatch
        ? 'Volte à seleção e escolha os arquivos originais. Para começar de novo, use Nova seleção.'
        : locked
          ? 'O envio foi preservado para recuperação. Volte à página e use Retomar envio quando estiver pronto.'
          : 'Sua seleção foi mantida. Volte à página para revisar e tentar novamente.'
    "
    :dismiss-label="mismatch ? 'Voltar à seleção' : 'Voltar ao envio'"
    @close="closeError"
  />
  <q-banner v-if="cadastro && !cadastro.disponivel" class="info-banner q-mb-lg">
    A base cadastral ainda não está disponível. A importação pode ser enviada,
    mas a análise precisa do CSV cadastral, separado do JSON de regras.
    <RegistryImport @imported="loadSetup" />
  </q-banner>
  <q-banner v-if="locked" class="info-banner q-mb-lg">
    Importação preservada para recuperação. Após recarregar a página, selecione
    os mesmos arquivos, na mesma ordem.
    <q-btn flat label="Nova seleção" :disable="busy" @click="confirmReset" />
  </q-banner>
  <div class="upload-grid">
    <section class="surface">
      <div class="surface-head">
        <h2>Nova importação</h2>
        <span class="text-caption text-grey-7">01 / Envio dos arquivos</span>
      </div>
      <div class="q-pa-lg">
        <q-input
          ref="nameInput"
          outlined
          v-model="name"
          :readonly="locked || busy"
          :error="!!nameError"
          :error-message="nameError"
          hint="Obrigatório · até 120 caracteres"
          counter
          @blur="nameTouched = true"
          maxlength="120"
          label="Nome do lote"
          placeholder="Ex.: Recebíveis · Outubro 2026"
        />
      </div>
      <div
        ref="fileArea"
        tabindex="-1"
        role="group"
        aria-label="Seleção de arquivos"
        class="upload-zone"
        @dragover.prevent
        @drop.prevent="select($event.dataTransfer?.files ?? null)"
      >
        <q-icon name="cloud_upload" size="42px" />
        <h3>Seus recebíveis, em um só lugar.</h3>
        <p class="subtitle">
          Arraste os arquivos aqui ou selecione no seu computador.
        </p>
        <q-btn
          class="q-mt-md"
          color="primary"
          outline
          label="Selecionar arquivos"
          :disable="busy"
          @click="input?.click()"
        />
        <input
          ref="input"
          type="file"
          hidden
          multiple
          accept=".csv,.xlsx"
          @change="select(($event.target as HTMLInputElement).files)"
        />
        <p class="text-caption text-grey-7 q-mt-md">
          CSV ou XLSX · até
          {{
            caps
              ? Math.min(caps.max_bytes_arquivo, caps.max_bytes_batch) / 1048576
              : "—"
          }}
          MiB por arquivo
        </p>
        <p v-if="selectionError" role="alert" class="text-negative">
          {{ selectionError }}
        </p>
      </div>
      <q-list separator>
        <q-item v-for="(file, i) in files" :key="i">
          <q-item-section avatar><q-icon name="description" /></q-item-section>
          <q-item-section>
            {{ file.name }}
            <q-item-label caption>
              {{ (file.size / 1024).toFixed(1) }} KiB · posição {{ i + 1 }}
            </q-item-label>
            <q-item-label
              v-if="fileError(file)"
              caption
              class="text-negative"
              role="alert"
            >
              {{ fileError(file) }}
            </q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-btn
              v-if="!locked"
              :disable="busy"
              flat
              round
              icon="close"
              :aria-label="`Remover ${file.name}`"
              @click="files.splice(i, 1)"
            />
          </q-item-section>
        </q-item>
      </q-list>
      <div class="q-pa-lg">
        <div v-if="busy" role="status" class="q-mb-md">
          {{ phase }}
          <q-linear-progress
            class="q-mt-sm"
            :value="progress"
            :indeterminate="progress === 0"
          />
        </div>
        <q-btn
          color="primary"
          :label="locked ? 'Retomar envio' : 'Enviar recebíveis'"
          icon-right="arrow_forward"
          :loading="busy"
          :disable="!caps"
          @click="submit"
        />
        <span class="q-ml-md text-caption text-grey-7">
          {{ files.length }} arquivo(s) selecionado(s)
        </span>
      </div>
    </section>
    <aside>
      <div class="surface help-card">
        <div class="eyebrow">COMO FUNCIONA</div>
        <h3>Clareza em cada etapa</h3>
        <p>
          <strong>01 · Importe</strong>
          <br />
          Selecione CSV ou XLSX. Arquivos ZIP devem ser extraídos antes do
          envio.
        </p>
        <p>
          <strong>02 · Acompanhe</strong>
          <br />
          O sistema prepara os dados e identifica as configurações pendentes por
          fundo.
        </p>
        <p>
          <strong>03 · Consulte</strong>
          <br />
          Veja aprovações, recusas, motivos e valores líquidos retornados pela
          análise.
        </p>
        <q-separator class="q-my-lg" />
        <p>
          Até {{ caps?.max_arquivos_lote ?? "—" }} arquivos e
          {{ caps?.max_linhas_lote.toLocaleString("pt-BR") ?? "—" }} linhas por
          lote. O limite de linhas é validado pelo servidor.
        </p>
      </div>
    </aside>
  </div>
</template>
