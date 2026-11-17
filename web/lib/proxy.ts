const COOKIE = "steadyday_demo";
const TOKEN = /^[A-Za-z0-9_-]{43}$/;
const BODY_LIMIT = 2048;
const CHECKIN_BODY_LIMIT = 8192;
const allowed = {
  config: ["GET"],
  dashboard: ["GET"],
  insights: ["GET"],
  profile: ["GET", "PUT"],
  "check-in": ["GET", "PUT", "DELETE"],
  goals: ["GET", "PUT"],
  goal: ["POST", "PUT", "DELETE"],
  habits: ["GET", "PUT"],
  habit: ["POST", "PUT", "DELETE"],
  reminder: ["PUT"],
  export: ["GET"],
  session: ["POST", "DELETE"],
} as const;
type Resource = keyof typeof allowed;
export type ProxySettings = Readonly<{ baseURL?: string; origin?: string; key?: string }>;
type UpstreamFetch = typeof fetch;

const errorMessages: Record<string,string> = {
  BACKEND_UNAVAILABLE: "The demo service is temporarily unavailable.",
  SESSION_REQUIRED: "Start a new demo or resume an active one.",
  SESSION_EXISTS: "Continue your existing demo or delete it first.",
  ORIGIN: "Open the demo directly to make changes.",
  PAYLOAD_LIMIT: "The demo request is too large or empty.",
  CONTENT_TYPE: "Send JSON.",
  NOT_FOUND: "This demo route does not exist.",
};

function failure(status: number, code: string) {
  return Response.json({ error: { code, message: errorMessages[code] ?? "The demo request could not be completed." } },
    { status, headers: { "Cache-Control": "no-store" } });
}
function originFor(request: Request, value?: string): string | null {
  try {
    const url = new URL(value ?? request.url);
    if (value && (url.origin !== value || !["https:", "http:"].includes(url.protocol))) return null;
    if (!value && !["127.0.0.1","localhost","[::1]"].includes(url.hostname)) return null;
    if (url.protocol !== "https:" && !["127.0.0.1","localhost","[::1]"].includes(url.hostname)) return null;
    return url.origin;
  } catch { return null; }
}
function sessionToken(request: Request): string {
  for (const part of (request.headers.get("cookie") ?? "").split(";")) {
    const [key, value] = part.trim().split("=", 2);
    if (key === COOKIE && value && TOKEN.test(value)) return value;
  }
  return "";
}
function responseCookie(token: string, ttl: number, secure: boolean): string {
  return COOKIE + "=" + token + "; Path=/; HttpOnly; SameSite=Strict; Max-Age=" + String(ttl) + (secure ? "; Secure" : "");
}
async function boundedBody(request: Request, limit: number): Promise<string | null> {
  const size = request.headers.get("content-length");
  if (size && (!/^\d{1,6}$/.test(size) || Number(size) > limit)) return null;
  if (!request.body) return null;
  const read = request.body.getReader();
  let total = 0, text = "";
  const decoder = new TextDecoder("utf-8", { fatal: true });
  try {
    while (true) {
      const { done, value } = await read.read();
      if (done) break;
      total += value.byteLength;
      if (total > limit) {
        void read.cancel().catch(() => {});
        return null;
      }
      text += decoder.decode(value, { stream: true });
    }
    return text + decoder.decode() || null;
  } catch { return null; }
  finally { read.releaseLock(); }
}

export async function proxyDemo(
  request: Request, resource: string, cfg: ProxySettings, upstream: UpstreamFetch = fetch
): Promise<Response> {
  if (!Object.hasOwn(allowed, resource) || !(allowed[resource as Resource] as readonly string[]).includes(request.method)) {
    return failure(404, "NOT_FOUND");
  }
  const method = request.method;
  const origin = originFor(request, cfg.origin);
  if (method !== "GET" && (!origin || request.headers.get("origin") !== origin)) return failure(403, "ORIGIN");
  let url: URL;
  try {
    url = new URL(cfg.baseURL ?? "");
    if (url.username || url.password || url.search || url.hash || url.pathname !== "/" ||
        !(url.protocol === "https:" || (url.protocol === "http:" && ["127.0.0.1","localhost","[::1]"].includes(url.hostname)))) {
      throw new Error("Invalid API origin");
    }
  } catch { return failure(503, "BACKEND_UNAVAILABLE"); }
  const token = sessionToken(request);
  if (!token && resource !== "config" && !(resource === "session" && method === "POST")) return failure(401, "SESSION_REQUIRED");

  let body: string | undefined;
  if (method === "POST" || method === "PUT") {
    if ((request.headers.get("content-type") ?? "").split(";")[0]?.trim().toLowerCase() !== "application/json") {
      return failure(415, "CONTENT_TYPE");
    }
    const value = await boundedBody(request, resource === "check-in" ? CHECKIN_BODY_LIMIT : BODY_LIMIT);
    if (!value) return failure(413, "PAYLOAD_LIMIT");
    body = value;
  }
  const headers = new Headers({ accept: "application/json" });
  if (token) headers.set("authorization", "Bearer " + token);
  if (cfg.key) headers.set("x-proxy-key", cfg.key);
  if (body) headers.set("content-type", "application/json");
  const send = (path: string, verb: string, payload?: string) => {
    const target = new URL("/v1/" + path, url);
    const queryName = path === "insights" ? "days" :
      path === "check-in" && verb !== "PUT" ? "day" :
      verb === "DELETE" && (path === "goal" || path === "habit") ? "id" : null;
    if (queryName) {
      const queryValue = new URL(request.url).searchParams.get(queryName);
      if (queryValue !== null) target.searchParams.set(queryName, queryValue);
    }
    return upstream(target, { method: verb, headers, body: payload, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(5000) });
  };
  try {
    if (resource === "session" && method === "POST" && token) {
      const existing = await send("dashboard", "GET");
      if (existing.ok) return failure(409, "SESSION_EXISTS");
      if (existing.status !== 401) return failure(503, "BACKEND_UNAVAILABLE");
    }
    const response = await send(resource, method, body);
    if (response.status >= 500) return failure(503, "BACKEND_UNAVAILABLE");
    const value: unknown = await response.json();
    if (typeof value !== "object" || value === null) return failure(503, "BACKEND_UNAVAILABLE");
    const output = new Headers({ "Cache-Control": "no-store" });
    if (resource === "session" && method === "POST" && response.ok) {
      const result = value as { session_token?: unknown; expires_in?: unknown };
      const session = result.session_token;
      const ttl = result.expires_in;
      if (typeof session !== "string" || !TOKEN.test(session) || typeof ttl !== "number" || !Number.isInteger(ttl) || ttl < 1 || ttl > 2592000) {
        return failure(503, "BACKEND_UNAVAILABLE");
      }
      output.set("set-cookie", responseCookie(session, ttl, Boolean(origin?.startsWith("https://"))));
      return Response.json({ created: true }, { status: 201, headers: output });
    }
    if (resource === "session" && method === "DELETE" && response.ok) {
      output.set("set-cookie", responseCookie("", 0, Boolean(origin?.startsWith("https://"))));
    }
    if (resource === "export" && response.ok) output.set("content-disposition", 'attachment; filename="steadyday-demo.json"');
    return Response.json(value, { status: response.status, headers: output });
  } catch { return failure(503, "BACKEND_UNAVAILABLE"); }
}
