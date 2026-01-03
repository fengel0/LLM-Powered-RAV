// ---------- URL helpers ----------
function isAbsolute(url) {
  return /^https?:\/\//i.test(url);
}

function trimSlashes(s = "") {
  return s.replace(/^\/+|\/+$/g, "");
}

function joinUrl(...parts) {
  return "/" + parts.map(trimSlashes).filter(Boolean).join("/");
}

/**
 * Ensure we include PATH_PREFIX for same-origin relative calls.
 * If apiBase is absolute (e.g., https://api.example.com/v1), use as-is.
 * If apiBase is blank or relative, build: {origin}/{PATH_PREFIX}/{apiBase}
 */
function resolveBase(apiBase) {
  const prefix = (window.PATH_PREFIX ?? "").toString();
  if (isAbsolute(apiBase)) return apiBase;
  const base = apiBase || "v1"; // sensible default if caller passes ""
  return location.origin + joinUrl(prefix, base);
}

// Normalize to a proper /v1 base regardless of how the caller passes apiUrl
function ensureV1Base(apiUrl) {
  // If apiUrl already ends with /v1, keep it; if it ends without, append /v1
  const base = resolveBase(apiUrl || "");
  return /\/v1\/?$/i.test(base) ? base.replace(/\/$/, "") : base + "/v1";
}

// ---------- API calls ----------
export async function fetchModels(apiUrl) {
  const v1 = ensureV1Base(apiUrl);
  const modelsUrl = v1 + "/models";
  const response = await fetch(modelsUrl, { headers: { "Content-Type": "application/json" } });
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  return response.json(); // { data: [...] }
}

export function chatUrl(apiUrl) {
  const v1 = ensureV1Base(apiUrl);
  return v1 + "/chat/completions";
}

export async function fetchContextById(apiUrl, contextId) {
  if (!contextId) return [];
  const v1 = ensureV1Base(apiUrl);
  const url = v1 + "/contexts/" + encodeURIComponent(contextId);
  const res = await fetch(url, { headers: { "Content-Type": "application/json" } });
  if (!res.ok) throw new Error(`Context fetch failed (${res.status}): ${res.statusText}`);
  const json = await res.json();
  return Array.isArray(json.data) ? json.data : [];
}
