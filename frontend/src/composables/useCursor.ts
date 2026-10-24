import { ref, shallowRef } from "vue";
export function useCursor<T>(
  loader: (
    cursor?: string,
  ) => Promise<{ itens: T[]; proximo_cursor: string | null }>,
) {
  const rows = shallowRef<T[]>([]),
    loading = ref(false),
    error = shallowRef<unknown>(null),
    next = ref<string | null>(null),
    history = ref<(string | undefined)[]>([undefined]);
  let generation = 0;
  async function load(reset = false) {
    if (reset) history.value = [undefined];
    const run = ++generation;
    loading.value = true;
    error.value = null;
    try {
      const page = await loader(history.value.at(-1));
      if (run === generation) {
        rows.value = page.itens;
        next.value = page.proximo_cursor;
      }
    } catch (e) {
      if (run === generation) {
        error.value = e;
        rows.value = [];
        next.value = null;
      }
    } finally {
      if (run === generation) loading.value = false;
    }
  }
  async function forward() {
    if (next.value) {
      history.value.push(next.value);
      await load();
    }
  }
  async function back() {
    if (history.value.length > 1) {
      history.value.pop();
      await load();
    }
  }
  return { rows, loading, error, next, history, load, forward, back };
}
