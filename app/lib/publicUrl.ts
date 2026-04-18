/**
 * When the UI is on Cloudflare Pages and the API/static files are on another
 * origin (e.g. Render), set VITE_API_BASE_URL at build time so /api and /static
 * resolve to the backend host.
 */
const API_ORIGIN =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export const API_ROOT = API_ORIGIN ? `${API_ORIGIN}/api` : "/api";

/** Prefix a backend-relative path (e.g. /static/audio/...) with the API origin when configured. */
export function publicBackendUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (API_ORIGIN && path.startsWith("/")) return `${API_ORIGIN}${path}`;
  return path;
}
