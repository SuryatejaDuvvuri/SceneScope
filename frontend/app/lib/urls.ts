const rawBackendUrl = (import.meta.env.VITE_API_BASE_URL || "").trim();

export const BACKEND_URL = rawBackendUrl.replace(/\/$/, "");

export function buildApiUrl(path: string): string {
  if (!BACKEND_URL) return path;
  return `${BACKEND_URL}${path}`;
}

export function buildAssetUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  if (!BACKEND_URL) return path;
  return `${BACKEND_URL}${path}`;
}
