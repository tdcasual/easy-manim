type JsonObject = Record<string, unknown>;

function apiBaseUrl(): string {
  // Prefer same-origin (Vite can proxy /api in dev).
  const base = (import.meta as any).env?.VITE_API_BASE_URL;
  return typeof base === "string" ? base.replace(/\/+$/, "") : "";
}

async function readJson(response: Response): Promise<JsonObject> {
  const text = await response.text();
  if (!text) return {};
  try {
    const parsed = JSON.parse(text);
    return typeof parsed === "object" && parsed !== null ? (parsed as JsonObject) : {};
  } catch {
    return {};
  }
}

export async function postSession(agentToken: string): Promise<{
  session_token: string;
  agent_id: string;
  name: string;
  expires_at: string;
}> {
  const response = await fetch(`${apiBaseUrl()}/api/sessions`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ agent_token: agentToken })
  });
  const payload = await readJson(response);
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : "login_failed";
    throw new Error(detail);
  }
  return payload as any;
}

