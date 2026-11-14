/** Thin fetch wrapper: same-origin /api, session cookie, CSRF double-submit header, typed errors. */

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function csrfToken(): string {
  const match = document.cookie.match(/(?:^|; )mediai_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

function messageFrom(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0] as { msg?: string; loc?: unknown[] };
    const field = Array.isArray(first.loc) ? String(first.loc[first.loc.length - 1]) : "";
    const msg = (first.msg ?? "Données invalides").replace(/^Value error, /, "");
    return field && field !== "body" ? `${field} : ${msg}` : msg;
  }
  if (status === 429) return "Trop de requêtes, réessayez dans quelques minutes.";
  return status >= 500 ? "Le serveur rencontre un problème, réessayez." : "Requête invalide.";
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (method !== "GET" && method !== "HEAD") headers.set("X-CSRF-Token", csrfToken());

  let res: Response;
  try {
    res = await fetch(`/api${path}`, { ...init, method, headers, credentials: "same-origin", cache: "no-store" });
  } catch {
    throw new ApiError(0, "Serveur injoignable. Vérifiez que le backend est démarré.");
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth/")) {
      window.location.href = `/connexion?suite=${encodeURIComponent(window.location.pathname)}`;
    }
    throw new ApiError(res.status, messageFrom((body as { detail?: unknown }).detail, res.status));
  }
  return body as T;
}

export type StreamHandlers = {
  onDelta: (text: string) => void;
  onError: (message: string) => void;
  onDone: () => void;
};

/** POST that consumes the Server-Sent Events stream of a chat answer. */
export async function streamChat(conversationId: string, content: string, h: StreamHandlers): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`/api/conversations/${conversationId}/messages`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
      body: JSON.stringify({ content }),
    });
  } catch {
    h.onError("Serveur injoignable.");
    h.onDone();
    return;
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    h.onError(messageFrom((body as { detail?: unknown }).detail, res.status));
    h.onDone();
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) >= 0) {
      const raw = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const event = /^event: (.*)$/m.exec(raw)?.[1];
      const data = /^data: (.*)$/m.exec(raw)?.[1];
      if (!event || !data) continue;
      const payload = JSON.parse(data) as { text?: string; message?: string };
      if (event === "delta" && payload.text) h.onDelta(payload.text);
      if (event === "error") h.onError(payload.message ?? "Erreur du chatbot.");
    }
  }
  h.onDone();
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
}
