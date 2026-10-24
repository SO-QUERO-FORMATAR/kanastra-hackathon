export function money(value: string | null | undefined) {
  if (value == null) return "—";
  const [whole, decimal = "00"] = value.split(".");
  return `${whole.startsWith("-") ? "-" : ""}R$ ${whole.replace("-", "").replace(/\B(?=(\d{3})+(?!\d))/g, ".")},${decimal.padEnd(2, "0")}`;
}
export const dateTime = (v: string) =>
  new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Sao_Paulo",
  }).format(new Date(v));
export const label = (v: string) =>
  v
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/^./, (s) => s.toUpperCase());
export async function sha256(file: File) {
  return Array.from(
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", await file.arrayBuffer()),
    ),
  )
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
export function batches<T extends { tamanho_bytes: number }>(
  items: T[],
  count: number,
  bytes: number,
) {
  const out: T[][] = [];
  let group: T[] = [];
  let size = 0;
  for (const item of items) {
    if (item.tamanho_bytes > bytes)
      throw Error("Arquivo excede o limite do batch.");
    if (group.length === count || size + item.tamanho_bytes > bytes) {
      out.push(group);
      group = [];
      size = 0;
    }
    group.push(item);
    size += item.tamanho_bytes;
  }
  if (group.length) out.push(group);
  return out;
}
