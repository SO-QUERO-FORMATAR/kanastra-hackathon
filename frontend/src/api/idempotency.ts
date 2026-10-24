import { storagePrefix } from "./client";
type SavedKey = { fingerprint: string; key: string; at: number };
/** Retain every rule mutation key for at least 24h, including confirmed writes. */
export function ruleMutationKey(fundId: string, body: unknown): string {
  const storageKey = storagePrefix + "rules." + fundId;
  const raw = localStorage.getItem(storageKey);
  const parsed = raw ? JSON.parse(raw) : [];
  const entries: SavedKey[] = Array.isArray(parsed) ? parsed : [];
  const retained = entries.filter((entry) => Date.now() - entry.at < 86400000);
  const fingerprint = JSON.stringify(body);
  let match = retained.find((entry) => entry.fingerprint === fingerprint);
  if (!match) {
    match = { fingerprint, key: crypto.randomUUID(), at: Date.now() };
    retained.push(match);
  }
  localStorage.setItem(storageKey, JSON.stringify(retained));
  return match.key;
}
